"""FastAPI app serving the HTMX-powered web UI."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from assistant.llm import LLMClient
from assistant.repo import get_project_root, read_markdown, write_text
from assistant.runner import list_skills, run_skill
from assistant.schemas import InputMetadata
from assistant.settings import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="LIS Personal Assistant", version="0.1.0")

ROOT = get_project_root()
STATIC_DIR = ROOT / "static"

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        api_key=settings.openai_api_key or None,
        default_model=settings.openai_model,
    )


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

_LAYOUT_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>LIS Assistant</title>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; }
  .htmx-indicator { display: none; }
  .htmx-request .htmx-indicator { display: inline-block; }
  pre { white-space: pre-wrap; word-break: break-word; }
  textarea { min-height: 12rem; }
</style>
</head>
"""

_NAV = """\
<nav class="bg-gray-900 text-white px-4 py-3 flex items-center gap-6 text-sm">
  <a href="/" class="font-bold text-lg tracking-tight">LIS Assistant</a>
  <a href="/" class="hover:text-blue-300">Run</a>
  <a href="/history" class="hover:text-blue-300">History</a>
  <a href="/usage" class="hover:text-blue-300">Usage</a>
</nav>
"""


def _page(body: str) -> HTMLResponse:
    html = (
        _LAYOUT_HEAD
        + "<body class='bg-gray-50 min-h-screen'>"
        + _NAV
        + '<main class="max-w-3xl mx-auto px-4 py-6">'
        + body
        + "</main></body></html>"
    )
    return HTMLResponse(html)


def _card(title: str, content: str) -> str:
    return (
        f'<div class="bg-white rounded-lg shadow p-6 mb-6">'
        f'<h2 class="text-lg font-semibold mb-4">{title}</h2>'
        f"{content}</div>"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page: paste input, pick skill, run."""
    skills = list_skills(ROOT)
    skill_options = "".join(
        f'<option value="{s.name}">{s.name} — {s.description}</option>' for s in skills
    )

    form = f"""\
    <form hx-post="/run" hx-target="#result" hx-indicator="#spinner" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Skill</label>
        <select name="skill_name"
                class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
          {skill_options}
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Input text</label>
        <textarea name="input_text"
                  placeholder="Paste your transcript, email, or notes here..."
                  class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows="10"></textarea>
      </div>

      <details class="text-sm">
        <summary class="cursor-pointer text-gray-500 hover:text-gray-700">Optional metadata</summary>
        <div class="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label class="block text-xs text-gray-500 mb-1">Module</label>
            <input name="module" type="text"
                   class="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"/>
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Module code</label>
            <input name="module_code" type="text"
                   class="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"/>
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Week</label>
            <input name="week" type="number"
                   class="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"/>
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Session</label>
            <input name="session" type="number"
                   class="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"/>
          </div>
        </div>
      </details>

      <button type="submit"
              class="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md font-medium hover:bg-blue-700 transition text-sm">
        Run skill
      </button>
      <span id="spinner" class="htmx-indicator text-sm text-gray-400 ml-2">Processing...</span>
    </form>
    """
    body = _card("Run a Skill", form) + '<div id="result"></div>'
    return _page(body)


@app.post("/run", response_class=HTMLResponse)
async def run_skill_endpoint(
    skill_name: str = Form(...),
    input_text: str = Form(""),
    module: str = Form(""),
    module_code: str = Form(""),
    week: str = Form(""),
    session: str = Form(""),
):
    """Execute a skill and return the result as an HTML fragment."""
    if not input_text.strip():
        return HTMLResponse(
            '<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-4 text-sm">'
            "Please paste some text before running a skill.</div>"
        )

    metadata = InputMetadata(
        module=module.strip() or None,
        module_code=module_code.strip() or None,
        week=int(week) if week.strip() else None,
        session=int(session) if session.strip() else None,
    )

    try:
        llm_client = _get_llm_client()
        result = run_skill(
            skill_name=skill_name,
            input_text=input_text,
            metadata=metadata,
            llm_client=llm_client,
            base_dir=ROOT,
        )
    except Exception as exc:
        logger.exception("Skill execution failed")
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-4 text-sm">'
            f"Error: {exc}</div>"
        )

    # Build result HTML
    warnings_html = ""
    if result.warnings:
        items = "".join(f"<li>{w}</li>" for w in result.warnings)
        warnings_html = (
            f'<div class="bg-yellow-50 border border-yellow-200 text-yellow-800 '
            f'rounded-md p-3 text-sm mb-4"><ul class="list-disc ml-4">{items}</ul></div>'
        )

    usage_html = ""
    if result.usage:
        usage_html = (
            f'<p class="text-xs text-gray-400 mt-4">'
            f"Tokens: {result.usage.input_tokens} in / {result.usage.output_tokens} out "
            f"| Cost: ${result.usage.estimated_cost_usd:.4f} "
            f"| Model: {result.usage.model}</p>"
        )

    file_html = ""
    if result.output_file:
        file_html = (
            f'<p class="text-sm text-green-700 mb-3">'
            f"Saved to: <code>{result.output_file}</code></p>"
        )

    output_json = json.dumps(result.output_data, indent=2, default=str)

    result_html = (
        f'{warnings_html}{file_html}'
        f'<pre class="bg-gray-900 text-green-300 rounded-md p-4 text-xs overflow-x-auto'
        f' max-h-96 overflow-y-auto">{_escape_html(output_json)}</pre>'
        f'{usage_html}'
    )

    return HTMLResponse(_card("Result", result_html))


@app.get("/history", response_class=HTMLResponse)
async def history():
    """Show recent output files."""
    outputs_dir = ROOT / "outputs"
    files: list[tuple[Path, dict]] = []

    for sub in ("meetings", "lectures", "communications"):
        sub_dir = outputs_dir / sub
        if not sub_dir.is_dir():
            continue
        for f in sorted(sub_dir.glob("*.md"), reverse=True):
            try:
                meta, body = read_markdown(f)
                files.append((f, meta))
            except Exception:
                files.append((f, {}))

    if not files:
        return _page(
            _card("History", '<p class="text-gray-500 text-sm">No outputs yet.</p>')
        )

    rows = ""
    for fpath, meta in files[:30]:
        rel = str(fpath.relative_to(ROOT))
        title = meta.get("title", fpath.stem)
        ftype = meta.get("type", "—")
        fdate = meta.get("date", "—")
        rows += (
            f"<tr class='border-b border-gray-100 hover:bg-gray-50'>"
            f"<td class='py-2 px-3 text-sm'>"
            f"<a href='/view?path={rel}' class='text-blue-600 hover:underline'>{_escape_html(str(title))}</a>"
            f"</td>"
            f"<td class='py-2 px-3 text-sm text-gray-500'>{_escape_html(str(ftype))}</td>"
            f"<td class='py-2 px-3 text-sm text-gray-500'>{fdate}</td>"
            f"</tr>"
        )

    table = (
        '<table class="w-full text-left">'
        "<thead><tr class='border-b-2 border-gray-200'>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Title</th>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Type</th>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Date</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )

    return _page(_card("Recent Outputs", table))


@app.get("/view", response_class=HTMLResponse)
async def view_file(path: str):
    """View a single output file with option to edit."""
    file_path = ROOT / path
    if not file_path.exists() or not file_path.is_file():
        return _page(
            '<div class="bg-red-50 text-red-700 rounded-md p-4 text-sm">File not found.</div>'
        )

    content = file_path.read_text(encoding="utf-8")

    body = (
        f'<div class="mb-4">'
        f'<a href="/history" class="text-blue-600 hover:underline text-sm">&larr; Back to history</a>'
        f'</div>'
        f'<h2 class="text-lg font-semibold mb-2">{_escape_html(file_path.name)}</h2>'
        f'<p class="text-xs text-gray-400 mb-4">{_escape_html(path)}</p>'
        f'<form hx-post="/save" hx-target="#save-status">'
        f'<input type="hidden" name="path" value="{_escape_html(path)}"/>'
        f'<textarea name="content" rows="20"'
        f' class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono'
        f' focus:ring-2 focus:ring-blue-500 focus:border-blue-500">'
        f"{_escape_html(content)}</textarea>"
        f'<div class="flex gap-3 mt-3">'
        f'<button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded-md text-sm'
        f' font-medium hover:bg-blue-700 transition">Save changes</button>'
        f'<span id="save-status"></span>'
        f"</div></form>"
    )

    return _page(f'<div class="bg-white rounded-lg shadow p-6">{body}</div>')


@app.post("/save", response_class=HTMLResponse)
async def save_file(path: str = Form(...), content: str = Form(...)):
    """Save edited content back to the file."""
    file_path = ROOT / path
    if not file_path.exists():
        return HTMLResponse(
            '<span class="text-red-600 text-sm">File not found.</span>'
        )

    try:
        write_text(file_path, content)
        return HTMLResponse(
            '<span class="text-green-600 text-sm">Saved successfully.</span>'
        )
    except Exception as exc:
        return HTMLResponse(
            f'<span class="text-red-600 text-sm">Save failed: {exc}</span>'
        )


@app.get("/usage", response_class=HTMLResponse)
async def usage_page():
    """Show LLM usage stats."""
    log_path = ROOT / "outputs" / ".usage_log.jsonl"

    if not log_path.exists():
        return _page(
            _card("Usage", '<p class="text-gray-500 text-sm">No usage data yet.</p>')
        )

    total_cost = 0.0
    total_in = 0
    total_out = 0
    call_count = 0

    for line in log_path.read_text().strip().splitlines():
        try:
            rec = json.loads(line)
            total_cost += rec.get("estimated_cost_usd", 0)
            total_in += rec.get("input_tokens", 0)
            total_out += rec.get("output_tokens", 0)
            call_count += 1
        except json.JSONDecodeError:
            continue

    stats = (
        f'<div class="grid grid-cols-2 gap-4 text-sm">'
        f'<div class="bg-gray-50 rounded p-3"><span class="text-gray-500">Calls</span>'
        f'<p class="text-2xl font-bold">{call_count}</p></div>'
        f'<div class="bg-gray-50 rounded p-3"><span class="text-gray-500">Total cost</span>'
        f'<p class="text-2xl font-bold">${total_cost:.4f}</p></div>'
        f'<div class="bg-gray-50 rounded p-3"><span class="text-gray-500">Input tokens</span>'
        f'<p class="text-2xl font-bold">{total_in:,}</p></div>'
        f'<div class="bg-gray-50 rounded p-3"><span class="text-gray-500">Output tokens</span>'
        f'<p class="text-2xl font-bold">{total_out:,}</p></div>'
        f"</div>"
    )

    return _page(_card("LLM Usage", stats))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
