"""Knowledge retrieval layer: find relevant source files for grounding skill outputs.

V1 strategy: folder scoping + frontmatter filtering + keyword search.
No embeddings — deterministic and predictable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from assistant.repo import list_files_with_frontmatter, read_markdown
from assistant.schemas import ContextDocument

# Keywords that trigger automatic inclusion of policy documents
POLICY_TRIGGER_WORDS = frozenset(
    [
        "deadline",
        "extension",
        "submission",
        "attendance",
        "mitigating",
        "circumstances",
        "late",
        "penalty",
        "plagiarism",
        "academic integrity",
    ]
)


def retrieve_context(
    base_dir: Path,
    source_scopes: list[str],
    input_text: str = "",
    module: str | None = None,
    module_code: str | None = None,
    max_documents: int = 10,
    max_chars_per_doc: int = 4000,
) -> list[ContextDocument]:
    """Retrieve relevant context documents for a skill execution.

    Strategy:
    1. Scan each source_scope folder
    2. Filter by module if provided
    3. Auto-include policy docs if input mentions policy-related keywords
    4. Rank by relevance (module match > keyword match > recency)
    5. Cap at max_documents to avoid overwhelming the LLM context
    """
    candidates: list[tuple[float, ContextDocument]] = []

    for scope in source_scopes:
        scope_dir = base_dir / scope
        if not scope_dir.is_dir():
            continue

        for file_path, meta in list_files_with_frontmatter(scope_dir):
            score = _score_document(
                file_path, meta, input_text, module, module_code, scope
            )
            if score <= 0:
                continue

            try:
                _, body = read_markdown(file_path)
            except Exception:
                continue

            truncated = body[:max_chars_per_doc]
            if len(body) > max_chars_per_doc:
                truncated += "\n\n[... truncated ...]"

            rel_path = str(file_path.relative_to(base_dir))
            doc = ContextDocument(
                title=meta.get("title", file_path.stem),
                path=rel_path,
                content=truncated,
                metadata=meta,
            )
            candidates.append((score, doc))

    # Check for policy trigger words — if present, ensure policies are included
    if _has_policy_triggers(input_text):
        _boost_policy_docs(candidates, base_dir, max_chars_per_doc)

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in candidates[:max_documents]]


def _score_document(
    file_path: Path,
    meta: dict[str, Any],
    input_text: str,
    module: str | None,
    module_code: str | None,
    scope: str,
) -> float:
    """Score a document for relevance. Higher = more relevant."""
    score = 1.0

    doc_module = meta.get("module", "")
    doc_module_code = meta.get("module_code", "")

    if module and doc_module:
        if module.lower() == doc_module.lower():
            score += 5.0
        elif module.lower() in doc_module.lower():
            score += 2.0

    if module_code and doc_module_code:
        if module_code.upper() == doc_module_code.upper():
            score += 5.0

    # Boost assessment and policy docs
    doc_type = meta.get("type", "")
    if doc_type in ("assessment-brief", "policy"):
        score += 3.0
    elif doc_type in ("module-outline",):
        score += 2.0

    # Keyword overlap between input and file content
    if input_text:
        input_words = set(re.findall(r"\w{4,}", input_text.lower()))
        title_words = set(re.findall(r"\w{4,}", meta.get("title", "").lower()))
        overlap = len(input_words & title_words)
        score += min(overlap, 3)

    # Boost documents with final status
    if meta.get("status") == "final":
        score += 1.0

    return score


def _has_policy_triggers(text: str) -> bool:
    """Check if the input text contains words that should trigger policy retrieval."""
    text_lower = text.lower()
    return any(word in text_lower for word in POLICY_TRIGGER_WORDS)


def _boost_policy_docs(
    candidates: list[tuple[float, ContextDocument]],
    base_dir: Path,
    max_chars_per_doc: int,
) -> None:
    """Ensure policy documents are included when policy keywords are detected."""
    policy_dir = base_dir / "knowledge" / "policies"
    if not policy_dir.is_dir():
        return

    existing_paths = {doc.path for _, doc in candidates}

    for file_path, meta in list_files_with_frontmatter(policy_dir):
        rel_path = str(file_path.relative_to(base_dir))
        if rel_path in existing_paths:
            # Already present — just boost its score
            for i, (score, doc) in enumerate(candidates):
                if doc.path == rel_path:
                    candidates[i] = (score + 5.0, doc)
            continue

        try:
            _, body = read_markdown(file_path)
        except Exception:
            continue

        truncated = body[:max_chars_per_doc]
        doc = ContextDocument(
            title=meta.get("title", file_path.stem),
            path=rel_path,
            content=truncated,
            metadata=meta,
        )
        candidates.append((10.0, doc))


def search_by_keyword(
    base_dir: Path,
    directories: list[str],
    keyword: str,
    max_results: int = 5,
) -> list[ContextDocument]:
    """Simple keyword search across markdown files in specified directories."""
    results: list[ContextDocument] = []
    keyword_lower = keyword.lower()

    for dir_rel in directories:
        dir_path = base_dir / dir_rel
        if not dir_path.is_dir():
            continue

        for file_path, meta in list_files_with_frontmatter(dir_path):
            try:
                _, body = read_markdown(file_path)
            except Exception:
                continue

            title = meta.get("title", file_path.stem)
            if keyword_lower in body.lower() or keyword_lower in title.lower():
                rel_path = str(file_path.relative_to(base_dir))
                results.append(
                    ContextDocument(
                        title=title,
                        path=rel_path,
                        content=body[:4000],
                        metadata=meta,
                    )
                )
                if len(results) >= max_results:
                    return results

    return results
