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
  .htmx-request .htmx-indicator,
  .htmx-request.htmx-indicator { display: inline-flex; }
  .htmx-request button[type="submit"],
  form.htmx-request button[type="submit"] { opacity: 0.6; pointer-events: none; cursor: wait; }
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
  <a href="/publish" class="hover:text-blue-300">Publish</a>
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
    skills = [s for s in list_skills(ROOT) if s.prompt_template]
    skill_options = "".join(
        f'<option value="{s.name}">{s.name} — {s.description}</option>' for s in skills
    )

    form = f"""\
    <form hx-post="/run" hx-target="#result" class="space-y-4">
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
            <label class="block text-xs text-gray-500 mb-1">Chapter</label>
            <input name="chapter" type="text" placeholder="e.g. decision-trees"
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
              class="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md font-medium hover:bg-blue-700 transition text-sm flex items-center justify-center gap-2">
        <svg class="htmx-indicator animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
        Run skill
      </button>
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
    chapter: str = Form(""),
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
        chapter=chapter.strip() or None,
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

    # Show "Push to Notion" button if there are actions and Notion is configured
    notion_btn = ""
    actions = result.output_data.get("actions", [])
    if actions:
        from assistant.notion_sync import is_notion_configured

        if is_notion_configured(ROOT):
            actions_json = _escape_html(json.dumps(actions, default=str))
            source = _escape_html(result.output_file or "(pasted input)")
            spinner_svg = '<svg class="htmx-indicator animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>'
            notion_btn = (
                f'<form hx-post="/notion/sync" hx-target="#notion-result" hx-indicator="closest form" class="mt-4">'
                f'<input type="hidden" name="tasks_json" value="{actions_json}"/>'
                f'<input type="hidden" name="source_file" value="{source}"/>'
                f'<button type="submit" class="bg-purple-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-purple-700 transition flex items-center gap-2">'
                f'{spinner_svg} Push {len(actions)} task(s) to Notion</button>'
                f'</form><div id="notion-result" class="mt-2"></div>'
            )
        else:
            notion_btn = (
                f'<p class="text-xs text-gray-400 mt-3">'
                f'{len(actions)} task(s) extracted. '
                f'Configure NOTION_API_KEY and NOTION_TASK_DB_ID in .env to enable Notion sync.</p>'
            )

    result_html = (
        f'{warnings_html}{file_html}'
        f'<pre class="bg-gray-900 text-green-300 rounded-md p-4 text-xs overflow-x-auto'
        f' max-h-96 overflow-y-auto">{_escape_html(output_json)}</pre>'
        f'{notion_btn}{usage_html}'
    )

    return HTMLResponse(_card("Result", result_html))


@app.post("/notion/sync", response_class=HTMLResponse)
async def notion_sync_endpoint(
    tasks_json: str = Form(...),
    source_file: str = Form(""),
):
    """Push extracted tasks to Notion."""
    from assistant.notion_sync import sync_tasks
    from assistant.schemas import TaskItem

    try:
        tasks_raw = json.loads(tasks_json)
        tasks = [TaskItem(**t) for t in tasks_raw]
    except Exception as exc:
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-3 text-sm">'
            f"Failed to parse tasks: {exc}</div>"
        )

    try:
        result = sync_tasks(
            tasks=tasks,
            source_file=source_file or None,
            base_dir=ROOT,
        )
    except Exception as exc:
        logger.exception("Notion sync failed")
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-3 text-sm">'
            f"Notion sync error: {exc}</div>"
        )

    if result.errors:
        error_items = "".join(f"<li>{_escape_html(e)}</li>" for e in result.errors)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-3 text-sm">'
            f'<ul class="list-disc ml-4">{error_items}</ul></div>'
        )

    parts = []
    if result.created:
        items = "".join(f"<li>{_escape_html(t)}</li>" for t in result.created)
        parts.append(f'<p class="font-medium text-green-700">Created:</p><ul class="list-disc ml-4 text-sm">{items}</ul>')
    if result.skipped:
        items = "".join(f"<li>{_escape_html(t)}</li>" for t in result.skipped)
        parts.append(f'<p class="font-medium text-gray-500">Skipped (already exist):</p><ul class="list-disc ml-4 text-sm">{items}</ul>')

    return HTMLResponse(
        f'<div class="bg-green-50 border border-green-200 rounded-md p-3 text-sm">'
        f'{"".join(parts)}</div>'
    )


@app.get("/history", response_class=HTMLResponse)
async def history():
    """Show recent output files."""
    outputs_dir = ROOT / "outputs"
    files: list[tuple[Path, dict]] = []

    for sub in ("meetings", "lectures", "communications", "tasks"):
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
        f'<form hx-post="/save" hx-target="#save-status" hx-indicator="closest form">'
        f'<input type="hidden" name="path" value="{_escape_html(path)}"/>'
        f'<textarea name="content" rows="20"'
        f' class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono'
        f' focus:ring-2 focus:ring-blue-500 focus:border-blue-500">'
        f"{_escape_html(content)}</textarea>"
        f'<div class="flex gap-3 mt-3">'
        f'<button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded-md text-sm'
        f' font-medium hover:bg-blue-700 transition flex items-center gap-2">'
        f'<svg class="htmx-indicator animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>'
        f'Save changes</button>'
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
# Publish
# ---------------------------------------------------------------------------


@app.get("/publish", response_class=HTMLResponse)
async def publish_page():
    """Show publishable files and build controls."""
    from assistant.publisher import PublishConfig, scan_publishable

    config = PublishConfig(ROOT)
    publishable = scan_publishable(ROOT, config)

    if not publishable:
        hint = (
            '<p class="text-gray-500 text-sm">No publishable files found.</p>'
            '<p class="text-gray-400 text-xs mt-2">'
            'Add <code>publish: true</code> to the frontmatter of output files to include them.</p>'
        )
        return _page(_card("Publish", hint))

    rows = ""
    for pf in publishable:
        rel = str(pf.path.relative_to(ROOT))
        rows += (
            f"<tr class='border-b border-gray-100'>"
            f"<td class='py-2 px-3 text-sm'>"
            f"<a href='/view?path={_escape_html(rel)}' class='text-blue-600 hover:underline'>{_escape_html(pf.title)}</a>"
            f"</td>"
            f"<td class='py-2 px-3 text-sm text-gray-500'>{_escape_html(pf.module or '—')}</td>"
            f"<td class='py-2 px-3 text-sm text-gray-500 text-right'>{pf.week if pf.week is not None else '—'}</td>"
            f"<td class='py-2 px-3 text-sm text-gray-500 text-right'>{pf.session if pf.session is not None else '—'}</td>"
            f"</tr>"
        )

    table_html = (
        '<table class="w-full text-left">'
        "<thead><tr class='border-b-2 border-gray-200'>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Title</th>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Module</th>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase text-right'>Week</th>"
        "<th class='py-2 px-3 text-xs text-gray-500 uppercase text-right'>Session</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )

    spinner_svg = '<svg class="htmx-indicator animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>'

    build_form = (
        f'<form hx-post="/publish/build" hx-target="#build-result" class="mt-4">'
        f'<button type="submit" class="bg-green-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-green-700 transition flex items-center gap-2">'
        f'{spinner_svg} Build site ({len(publishable)} file{"s" if len(publishable) != 1 else ""})</button>'
        f'</form>'
        f'<div id="build-result" class="mt-3"></div>'
    )

    # Per-module deploy section
    from assistant.publisher import list_module_configs

    mod_configs = list_module_configs(ROOT)
    deployable = [m for m in mod_configs if m.has_remote]

    deploy_html = ""
    if deployable:
        deploy_rows = ""
        for mc in deployable:
            deploy_rows += (
                f"<tr class='border-b border-gray-100'>"
                f"<td class='py-2 px-3 text-sm font-medium'>{_escape_html(mc.site_name)}</td>"
                f"<td class='py-2 px-3 text-sm text-gray-500'><code class='text-xs'>{_escape_html(mc.remote)}</code></td>"
                f"<td class='py-2 px-3 text-right'>"
                f"<form hx-post='/publish/deploy' hx-target='#deploy-result-{mc.slug}' class='inline'>"
                f"<input type='hidden' name='module' value='{_escape_html(mc.slug)}'/>"
                f"<button type='submit' class='bg-indigo-600 text-white py-1 px-3 rounded text-xs font-medium hover:bg-indigo-700 transition flex items-center gap-1'>"
                f"{spinner_svg} Deploy</button>"
                f"</form></td></tr>"
                f"<tr><td colspan='3'><div id='deploy-result-{mc.slug}' class='mb-1'></div></td></tr>"
            )

        deploy_table = (
            '<table class="w-full text-left">'
            "<thead><tr class='border-b-2 border-gray-200'>"
            "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Module</th>"
            "<th class='py-2 px-3 text-xs text-gray-500 uppercase'>Remote</th>"
            "<th class='py-2 px-3 text-xs text-gray-500 uppercase text-right'>Action</th>"
            f"</tr></thead><tbody>{deploy_rows}</tbody></table>"
        )
        deploy_html = _card("Deploy to Remote Repos", deploy_table)

    body = _card(f"Publishable Files ({len(publishable)})", table_html + build_form)
    body += deploy_html
    return _page(body)


@app.post("/publish/build", response_class=HTMLResponse)
async def publish_build_endpoint():
    """Run the full publication pipeline."""
    from assistant.publisher import publish_all

    try:
        result = publish_all(ROOT, clean=True, build=True)
    except Exception as exc:
        logger.exception("Publish failed")
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 rounded-md p-4 text-sm">'
            f"Publish error: {_escape_html(str(exc))}</div>"
        )

    parts: list[str] = []

    parts.append(
        f'<p class="text-sm"><strong>{result["published"]}</strong> file(s) published, '
        f'config written to <code>{result["mkdocs_config"]}</code></p>'
    )

    if result.get("files"):
        file_items = "".join(f"<li class='text-xs text-gray-500'>{_escape_html(f)}</li>" for f in result["files"])
        parts.append(f'<ul class="list-disc ml-4 mt-2">{file_items}</ul>')

    if result.get("build_ok"):
        parts.append('<p class="text-green-700 font-medium mt-3">Site built successfully.</p>')
    elif "build_ok" in result:
        err = result.get("build_error", "unknown error")
        parts.append(f'<p class="text-red-700 font-medium mt-3">Build failed: {_escape_html(err)}</p>')

    css = "bg-green-50 border-green-200" if result.get("build_ok") else "bg-yellow-50 border-yellow-200"
    return HTMLResponse(
        f'<div class="{css} border rounded-md p-4 text-sm">{"".join(parts)}</div>'
    )


@app.post("/publish/deploy", response_class=HTMLResponse)
async def publish_deploy_endpoint(
    module: str = Form(...),
):
    """Deploy a single module to its remote repo."""
    from assistant.publisher import ModuleConfig, PublishConfig, deploy_module

    config = PublishConfig(ROOT)
    mod_dir = ROOT / config.source_dir / "modules" / module

    if not mod_dir.is_dir():
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 '
            f'rounded-md p-3 text-sm">Module not found: {_escape_html(module)}</div>'
        )

    mod_cfg = ModuleConfig(mod_dir)
    if not mod_cfg.has_remote:
        return HTMLResponse(
            f'<div class="bg-yellow-50 border border-yellow-200 text-yellow-700 '
            f'rounded-md p-3 text-sm">No remote configured for {_escape_html(module)}</div>'
        )

    try:
        result = deploy_module(mod_cfg, ROOT)
    except Exception as exc:
        logger.exception("Deploy failed for %s", module)
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 '
            f'rounded-md p-3 text-sm">Deploy error: {_escape_html(str(exc))}</div>'
        )

    status = result.get("status", "unknown")
    if status == "deployed":
        return HTMLResponse(
            f'<div class="bg-green-50 border border-green-200 text-green-700 '
            f'rounded-md p-3 text-sm">Deployed {result.get("files", 0)} '
            f'file(s) to {_escape_html(mod_cfg.remote)}</div>'
        )
    elif status == "up-to-date":
        return HTMLResponse(
            '<div class="bg-gray-50 border border-gray-200 text-gray-600 '
            'rounded-md p-3 text-sm">Already up to date.</div>'
        )
    else:
        err = result.get("error", result.get("reason", "unknown"))
        return HTMLResponse(
            f'<div class="bg-red-50 border border-red-200 text-red-700 '
            f'rounded-md p-3 text-sm">Deploy failed: {_escape_html(str(err))}</div>'
        )


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
