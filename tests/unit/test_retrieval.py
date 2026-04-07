"""Tests for the knowledge retrieval layer."""

from pathlib import Path

import frontmatter

from assistant.retrieval import retrieve_context, search_by_keyword


def _write_doc(path: Path, title: str, body: str, **meta):
    """Helper: write a markdown file with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, title=title, **meta)
    path.write_text(frontmatter.dumps(post) + "\n")


def test_retrieve_context_basic(tmp_path: Path):
    """Retrieve context scoped to a folder."""
    modules_dir = tmp_path / "knowledge" / "modules"
    _write_doc(
        modules_dir / "ai-ci.md",
        title="AI and Collective Intelligence",
        body="Module about AI and groups.",
        module="AI and Collective Intelligence",
        type="module-outline",
    )
    _write_doc(
        modules_dir / "other.md",
        title="Other Module",
        body="Unrelated module.",
        module="Data Science",
        type="module-outline",
    )

    docs = retrieve_context(
        base_dir=tmp_path,
        source_scopes=["knowledge/modules"],
        input_text="meeting about AI",
        module="AI and Collective Intelligence",
    )

    assert len(docs) >= 1
    titles = [d.title for d in docs]
    assert "AI and Collective Intelligence" in titles


def test_retrieve_context_empty_scope(tmp_path: Path):
    """Return empty list when scope directory doesn't exist."""
    docs = retrieve_context(
        base_dir=tmp_path,
        source_scopes=["nonexistent/folder"],
        input_text="anything",
    )
    assert docs == []


def test_policy_trigger_boosts(tmp_path: Path):
    """Policy docs are boosted when trigger words appear in input."""
    policies_dir = tmp_path / "knowledge" / "policies"
    _write_doc(
        policies_dir / "extensions.md",
        title="Extension Policy",
        body="Students must apply via mitigating circumstances.",
        type="policy",
    )

    docs = retrieve_context(
        base_dir=tmp_path,
        source_scopes=["knowledge/policies"],
        input_text="Can I get an extension for the deadline?",
    )

    assert len(docs) >= 1
    assert docs[0].title == "Extension Policy"


def test_search_by_keyword(tmp_path: Path):
    """Keyword search finds matching documents."""
    comms_dir = tmp_path / "knowledge" / "communications"
    _write_doc(
        comms_dir / "week1.md",
        title="Week 1 Update",
        body="Welcome to the module. First lecture on Monday.",
    )
    _write_doc(
        comms_dir / "week2.md",
        title="Week 2 Update",
        body="Assessment brief will be released soon.",
    )

    results = search_by_keyword(
        base_dir=tmp_path,
        directories=["knowledge/communications"],
        keyword="assessment",
    )

    assert len(results) == 1
    assert results[0].title == "Week 2 Update"
