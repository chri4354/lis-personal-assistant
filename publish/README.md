# Publishing to GitHub Pages

This directory is the source for a **book-style course site** powered by [MkDocs Material](https://squidfunnel.github.io/mkdocs-material/) and deployed to GitHub Pages — similar to [Think Python](https://allendowney.github.io/ThinkPython/).

The result is a navigable, searchable, mobile-friendly site with dark mode, organised by module, week, and session.

---

## How it works

```
outputs/lectures/  ──┐
outputs/meetings/  ──┤  publish build   ┌── publish/index.md
outputs/tasks/     ──┼─────────────────>│   publish/modules/<mod>/week-XX/session-XX.md
outputs/comms/     ──┘                  │   mkdocs.yml  (auto-generated)
                                        └──────────────┐
                                                       │  mkdocs build
                                                       ▼
                                                    site/   (static HTML)
                                                       │
                                                       │  git push → GitHub Actions
                                                       ▼
                                              GitHub Pages (live site)
```

1. You mark output files with `publish: true` in their YAML frontmatter.
2. The publish pipeline copies those files into `publish/modules/...` following a `module → week → session` hierarchy.
3. `mkdocs.yml` is auto-generated with a navigation tree built from the folder structure.
4. MkDocs builds the static HTML site into `site/`.
5. When you push to `main`, a GitHub Actions workflow deploys the site to GitHub Pages.

---

## Quick start

### 1. Mark a file for publication

Add `publish: true` to any output file's frontmatter. You also need `module`, `week`, and `session` for proper placement in the book:

```yaml
---
title: "Introduction to AI and Machine Learning"
type: lecture-page
module: "AI and ML"
week: 1
session: 1
publish: true
status: final
---

# Introduction to AI and Machine Learning

Content here...
```

### 2. Build the site locally

**From the CLI:**

```bash
# See which files are ready to publish
assistant publish list

# Run the full pipeline: copy files → generate config → build HTML
assistant publish build

# Preview locally at http://127.0.0.1:8001
assistant publish preview
```

**From the web UI:**

1. Go to http://127.0.0.1:8000/publish
2. Review the list of publishable files
3. Click **Build site**

### 3. Preview the result

After building, open the site locally:

```bash
assistant publish preview
```

This starts a local MkDocs dev server at http://127.0.0.1:8001 where you can see exactly how the published site will look — with navigation, search, and dark/light mode.

### 4. Deploy to GitHub Pages

**Option A: Automatic (recommended)**

Commit and push to `main`. The GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) will build and deploy automatically:

```bash
# Build first to generate mkdocs.yml and populate publish/
assistant publish build

# Commit the source content (not the built site — that's in .gitignore)
git add publish/ mkdocs.yml
git commit -m "Publish: add week 1 session 1 lecture notes"
git push
```

The workflow triggers whenever `publish/` or `mkdocs.yml` changes on `main`.

**Option B: Manual trigger**

Go to the Actions tab in your GitHub repository and run the **Deploy Course Book to GitHub Pages** workflow manually.

### 5. One-time GitHub setup

Before the first deployment, enable GitHub Pages in your repository:

1. Go to **Settings → Pages** in your GitHub repo
2. Under **Source**, select **GitHub Actions**
3. That's it — the workflow handles the rest

Your site will be available at `https://<username>.github.io/<repo-name>/`.

---

## Directory structure

```
publish/
├── index.md                          ← homepage (always present)
├── modules/
│   ├── ai-and-ml/
│   │   ├── index.md                  ← optional module overview
│   │   ├── week-01/
│   │   │   ├── session-01.md
│   │   │   └── session-02.md
│   │   └── week-02/
│   │       └── session-01.md
│   └── design-thinking/
│       └── week-01/
│           └── session-01.md
├── pages/                            ← files without a module
│   └── general-notes.md
└── README.md                         ← this file
```

This structure is **auto-generated** by `publish build` from your output files. You can also add files here manually — anything in `publish/` is included in the site.

---

## How navigation is generated

The nav tree in `mkdocs.yml` is built automatically:

- **Home** → `publish/index.md`
- **Module Name** (derived from folder name)
  - **Week 01** (from `week-XX` subdirectories)
    - **Session title** (from the first `# heading` in the file, or frontmatter `title`)
- **Pages** → files in `publish/pages/` without module grouping

Example generated nav:

```yaml
nav:
  - Home: index.md
  - Ai And Ml:
    - Week 01:
      - Introduction to AI: modules/ai-and-ml/week-01/session-01.md
      - Neural Networks: modules/ai-and-ml/week-01/session-02.md
    - Week 02:
      - Supervised Learning: modules/ai-and-ml/week-02/session-01.md
```

---

## What gets published (and what doesn't)

**Only files with `publish: true`** in their frontmatter are included. This is a safety mechanism:

- Meeting notes, internal actions, emails → **never published** (no `publish` flag)
- Lecture summaries you've reviewed → **published when you opt in**

This separation is enforced by `config/publish.yaml`:

```yaml
publish:
  filters:
    require_frontmatter_publish: true
```

---

## Configuration

All publish settings live in `config/publish.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `site_name` | Programme Course Book | Title shown in the site header |
| `site_url` | (empty) | Full URL of the deployed site |
| `theme` | material | MkDocs theme (material recommended) |
| `source_dir` | publish | Directory containing markdown source |
| `output_dir` | site | Directory for built HTML (gitignored) |
| `require_frontmatter_publish` | true | Only include files with `publish: true` |

---

## Tips

- **Edit before publishing**: review and edit output files in the web UI (`/view`) or your editor before adding `publish: true`
- **Rebuild is idempotent**: running `publish build` always produces the same result from the same inputs — safe to re-run
- **Manual pages**: you can add markdown files directly to `publish/` (e.g., a custom `publish/modules/ai-and-ml/index.md` module overview) — they'll be included in the nav
- **Clean builds**: `publish build` cleans `publish/modules/` and `publish/pages/` before copying, so removed or un-published files disappear from the site
- **Local preview vs deploy**: use `publish preview` for fast iteration; only push to `main` when you're happy with the result
