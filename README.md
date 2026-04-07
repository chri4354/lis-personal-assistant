# Programme Knowledge Management System — Developer Note / Build Plan

## Purpose

Build a lean, modular, text-first knowledge management and workflow system for running a master's programme. The system must be optimised for fast mobile use, low operational friction, and incremental extensibility. It should support capturing transcripts and notes, grounding actions and communications in authoritative programme documents, publishing selected material as a public course book, and optionally syncing structured tasks to Notion.

This document is written so that a developer, dev team, Codex, Claude Code, or another AI coding agent can use it as the implementation brief and architectural source of truth.

---

## 1. Product vision

The application is a personal operating system for programme management.

It should help the user:

- dump a transcript from a meeting, lecture, email, or voice note
    
- run a specific skill/workflow over that text input
    
- produce one or more outputs:
    
    - a structured markdown note
        
    - a grounded draft communication
        
    - a public class summary page
        
    - structured tasks for a Notion database
        
- store all durable knowledge in markdown files in a Git-backed repository
    
- publish selected markdown content as a GitHub Pages book-style site
    

The system must remain extremely lean:

- mostly text in / text out
    
- no complex audio/video pipelines in v1
    
- no heavy bespoke backend required for initial version
    
- modular skill architecture so new workflows can be added easily
    

---

## 2. Core design principles

### 2.1 Text-first

All primary inputs and outputs are text.

Inputs may include:

- meeting transcripts
    
- lecture transcripts
    
- pasted emails
    
- short notes
    
- voice note transcripts created elsewhere
    

Outputs may include:

- markdown meeting summaries
    
- markdown lecture pages
    
- email drafts
    
- Canvas announcement drafts
    
- structured task payloads for Notion
    

### 2.2 Markdown as durable knowledge

Markdown files in a Git repo are the canonical store for:

- module documents
    
- assessment briefs
    
- policies
    
- speaker notes
    
- processed meeting summaries
    
- processed lecture summaries
    
- public publishable content
    
- skill definitions and templates
    

### 2.3 Structured execution layer

Notion is optional but recommended as a thin execution layer for:

- tasks
    
- deadlines
    
- communication calendar
    
- schedule views
    

The system must work without Notion, but if Notion is enabled it should accept structured task output and push it to specific databases.

### 2.4 Grounded generation

All skill outputs that involve institutional communication must be grounded in authoritative documents.

Authoritative hierarchy:

1. assessment briefs
    
2. module documents
    
3. programme policies
    
4. speaker/schedule metadata
    
5. past communications
    
6. processed notes
    

The system must prefer quoting, paraphrasing, or explicitly citing internal source files over free-form generation.

### 2.5 Modular skills

Every workflow should be implemented as a skill with:

- clear purpose
    
- input contract
    
- source-of-truth documents
    
- output contract
    
- rules and constraints
    

Adding a new use case should require adding a new skill plus, optionally, a template and a route/command.

### 2.6 Mobile-first workflows

The system must optimise for:

- opening on mobile
    
- dropping text into an inbox
    
- choosing a workflow
    
- getting a useful output within seconds
    

---

## 3. Main user stories

### 3.1 Meeting to actions

As a user, I can paste a meeting transcript and run a workflow that:

- summarises the meeting
    
- extracts decisions
    
- extracts action points
    
- identifies deadlines if explicitly present
    
- writes a markdown summary file
    
- optionally pushes the tasks to a Notion database
    

### 3.2 Context-aware email drafting

As a user, I can paste an incoming email and run a workflow that:

- retrieves relevant briefs and policies
    
- drafts a response grounded in those documents
    
- avoids contradicting the source of truth
    

### 3.3 Lecture transcript to class page

As a user, I can paste a lecture transcript and run a workflow that:

- extracts key concepts
    
- extracts questions raised by students
    
- highlights clarifications and examples
    
- writes a clean markdown page for publication
    

### 3.4 Weekly student communication

As a user, I can generate a weekly communication draft that:

- summarises what happened this week
    
- previews what comes next
    
- includes deadlines and reminders
    
- is grounded in the teaching schedule and module content
    

### 3.5 Public book-style publication

As a user, I can publish selected class/session notes as a book-style site on GitHub Pages.

### 3.6 Extensible workflow architecture

As a user/admin, I can add a new skill and corresponding templates without redesigning the entire app.

---

## 4. Scope

### 4.1 In scope for v1

- repository structure generation
    
- local file-based knowledge base
    
- markdown templates
    
- skill definitions as files/configuration
    
- workflow runner for transcript/email/text inputs
    
- retrieval of relevant local files for grounding
    
- markdown outputs
    
- optional Notion task sync
    
- GitHub Pages publish pipeline for public notes
    
- mobile-friendly use through Obsidian + Working Copy or web app
    

### 4.2 Out of scope for v1

- native audio recording/transcription
    
- OCR-heavy document ingestion
    
- advanced multi-user permissions
    
- complex approval workflows
    
- full LMS integration with Canvas API
    
- bespoke iOS/Android app unless chosen later
    
- background autonomous agents performing unsupervised actions
    

---

## 5. Recommended architecture

There are two viable implementation paths.

## Option A — Lean local-first implementation

Best for fastest build and lowest complexity.

Components:

- file-based repo as source of truth
    
- simple local or lightweight web app UI
    
- LLM workflow runner
    
- local embeddings or lexical retrieval over markdown files
    
- Notion sync module
    
- static site generator for GitHub Pages
    

## Option B — Thin web app over repo

Best if a more guided UI is desired from the start.

Components:

- frontend web app
    
- backend API for workflow execution
    
- repo access layer
    
- retrieval layer
    
- Notion sync integration
    
- static publication pipeline
    

Recommendation: implement Option A first, but design interfaces so Option B can be added later.

---

## 6. Functional architecture

### 6.1 Core modules

#### A. Repository manager

Responsibilities:

- initialise folder structure
    
- read/write markdown files
    
- maintain metadata/frontmatter
    
- support path conventions
    
- expose helper methods for create/update/list/search
    

#### B. Knowledge retrieval layer

Responsibilities:

- find relevant source files for a workflow
    
- support retrieval by:
    
    - module
        
    - file type
        
    - folder
        
    - keyword
        
    - date
        
    - tags/frontmatter
        
- optionally support embeddings later
    

V1 can start with a hybrid of:

- folder-scoped retrieval
    
- frontmatter filters
    
- simple keyword/full-text search
    

#### C. Skill runner

Responsibilities:

- load skill definition
    
- validate input type
    
- collect source documents
    
- render prompt/context package
    
- call LLM
    
- validate output structure where needed
    
- write outputs
    
- trigger downstream actions like Notion sync
    

#### D. Template engine

Responsibilities:

- provide markdown templates for output files
    
- provide prompt templates for skills
    
- support configurable style/tone constraints
    

#### E. Notion integration

Responsibilities:

- map structured task output into Notion schema
    
- create/update tasks
    
- optionally read schedule/calendar databases later
    

#### F. Publisher

Responsibilities:

- transform selected markdown into book-style content
    
- push/build GitHub Pages site
    
- maintain navigation structure
    

#### G. Mobile UX layer

Possible implementations:

- Obsidian vault over repo
    
- simple web UI for inbox + workflow selection
    
- share sheet / shortcuts integration later
    

---

## 7. Repository structure

Recommended repository structure:

```text
programme-os/
├── inbox/
│   ├── transcripts/
│   ├── emails/
│   └── notes/
├── knowledge/
│   ├── modules/
│   ├── assessments/
│   ├── policies/
│   ├── speakers/
│   └── communications/
├── outputs/
│   ├── meetings/
│   ├── lectures/
│   └── communications/
├── publish/
│   ├── index.md
│   └── modules/
├── skills/
│   ├── meeting_to_actions.md
│   ├── email_reply.md
│   ├── lecture_to_page.md
│   ├── weekly_comm.md
│   └── notion_sync.md
├── templates/
│   ├── meeting.md
│   ├── lecture.md
│   ├── weekly_update.md
│   └── publish_session.md
├── config/
│   ├── app.yaml
│   ├── notion.yaml
│   └── publish.yaml
└── scripts/
```

---

## 8. File conventions

### 8.1 Markdown frontmatter

All durable markdown files should support YAML frontmatter.

Example:

```yaml
---
title: Week 3 Session 1
module: AI and Collective Intelligence
module_code: MASC-AICI-01
type: lecture-summary
date: 2026-10-12
week: 3
session: 1
status: final
publish: true
source_files:
  - ../../inbox/transcripts/2026-10-12-ai-ci-week3-session1.md
---
```

### 8.2 Naming conventions

Prefer predictable, sortable names.

Examples:

- `2026-10-12-module-board-meeting.md`
    
- `2026-10-15-week-03-session-01.md`
    
- `assessment-brief-final.md`
    
- `module-outline.md`
    

---

## 9. Skill file format

Each skill should be defined in a machine-readable and human-readable way.

Recommended format: YAML or JSON plus markdown description.

### 9.1 Suggested skill schema

```yaml
name: meeting_to_actions
description: Convert a meeting transcript into a structured meeting summary and action list.
input_type: transcript
input_location: inbox/transcripts
source_scopes:
  - knowledge/modules
  - knowledge/policies
  - outputs/meetings
outputs:
  markdown_note:
    path: outputs/meetings
    template: templates/meeting.md
  notion_tasks:
    enabled: true
rules:
  - Do not invent deadlines
  - Only create tasks that are explicit or strongly implied
  - Keep task titles atomic
llm:
  temperature: 0.2
```

### 9.2 Developer requirement

Skill definitions must be decoupled from code as much as possible. The runner should be able to load new skills from config files.

---

## 10. V1 skills

### 10.1 meeting_to_actions

Input:

- transcript
    

Sources:

- module docs if identifiable
    
- recent meeting notes
    
- policies if relevant
    

Outputs:

- markdown meeting summary
    
- list of structured task objects
    
- optional Notion sync
    

Markdown output sections:

- summary
    
- decisions
    
- action points
    
- open questions
    

Structured task schema:

- title
    
- description
    
- deadline (nullable)
    
- module (nullable)
    
- source_file
    
- status (default `todo`)
    

### 10.2 email_reply

Input:

- pasted email text
    

Sources:

- assessments
    
- modules
    
- policies
    
- past communication examples
    

Output:

- email draft
    

Rules:

- never contradict assessment brief
    
- if uncertain, state uncertainty rather than inventing policy
    
- tone: clear, concise, warm, professional
    

### 10.3 lecture_to_page

Input:

- lecture transcript
    

Sources:

- module outline
    
- weekly schedule
    
- reading list if available
    

Output:

- markdown page for publication
    

Sections:

- overview
    
- key concepts
    
- examples / case studies
    
- questions raised
    
- clarifications
    
- further reading
    

### 10.4 weekly_comm

Input:

- optional week identifier
    
- optional module identifier
    

Sources:

- module schedule
    
- lecture outputs
    
- deadlines from schedule/tasks
    

Output:

- Canvas-ready weekly announcement draft
    

### 10.5 notion_sync

Input:

- structured task array
    

Output:

- create/update in configured Notion database
    

---

## 11. Data contracts

### 11.1 Meeting summary object

```json
{
  "title": "Module Planning Meeting",
  "date": "2026-10-12",
  "summary": [
    "Agreed timeline for assessment release",
    "Confirmed external speaker for Week 5"
  ],
  "decisions": [
    "Publish assessment brief by Friday"
  ],
  "actions": [
    {
      "title": "Finalise assessment brief",
      "description": "Incorporate feedback and publish final brief",
      "deadline": "2026-10-16",
      "module": "AI and Collective Intelligence",
      "status": "todo"
    }
  ],
  "open_questions": [
    "Whether the Week 6 workshop should be extended"
  ]
}
```

### 11.2 Email draft object

```json
{
  "subject_suggestion": "Re: Assessment submission question",
  "body": "Thanks for your email ...",
  "grounding_sources": [
    "knowledge/assessments/module-x/assessment-brief-final.md"
  ],
  "warnings": []
}
```

### 11.3 Lecture page object

```json
{
  "title": "Week 3 Session 1 — Heuristics and Biases",
  "overview": "This session explored ...",
  "key_concepts": ["bounded rationality", "heuristics"],
  "examples": ["framing effect example"],
  "questions_raised": ["How do heuristics perform under uncertainty?"],
  "clarifications": ["System 1 and System 2 are descriptive models, not brain regions"],
  "further_reading": []
}
```

---

## 12. Retrieval strategy

V1 retrieval should be simple and deterministic.

### 12.1 Retrieval inputs

A workflow may optionally receive metadata such as:

- module name/code
    
- date
    
- week number
    
- content type
    

### 12.2 Retrieval rules

- If module is known, restrict retrieval to that module folder first
    
- Always include assessment briefs for assessment-related email workflows
    
- Always include policies when the prompt includes words like `deadline`, `extension`, `submission`, `attendance`, `mitigating circumstances`
    
- For lecture publication, include module outline and schedule
    
- For weekly communication, include schedule plus latest lecture outputs
    

### 12.3 Retrieval implementation v1

Implement using:

- frontmatter parsing
    
- folder scoping
    
- keyword search
    
- recent-file heuristics
    

Avoid embeddings unless recall is insufficient.

---

## 13. Prompting strategy

The LLM layer should use structured prompting with:

- explicit system instructions per skill
    
- injected source documents
    
- expected output schema
    
- hard constraints
    

### 13.1 Prompt anatomy

- role/purpose
    
- skill rules
    
- source-of-truth hierarchy
    
- relevant retrieved context
    
- output schema
    
- style guidance
    

### 13.2 Output validation

Where outputs are structured, validate with JSON schema or Pydantic models before writing or syncing.

---

## 14. Technology recommendations

## 14.1 Language

Python recommended for fastest delivery and best LLM/tooling ecosystem.

## 14.2 Suggested stack

- Python 3.11+
    
- FastAPI for optional thin backend/API
    
- Pydantic for schemas
    
- Typer or Click for CLI workflows
    
- Jinja2 for templates
    
- PyYAML for skill/config loading
    
- Markdown + frontmatter libraries
    
- Notion SDK for Python
    
- MkDocs Material or mdBook for GitHub Pages publication
    

Recommendation: prefer MkDocs Material for easiest book-style site.

### 14.3 Why MkDocs

- simple markdown-native workflow
    
- good navigation structure
    
- easy GitHub Pages deployment
    
- supports book/documentation-style output better than a raw Jekyll blog
    

---

## 15. Suggested implementation phases

## Phase 0 — Scaffolding

Deliverables:

- repo initialiser
    
- folder structure
    
- config files
    
- sample templates
    
- sample skills
    

## Phase 1 — Core local workflows

Deliverables:

- repository manager
    
- skill runner
    
- meeting_to_actions
    
- email_reply
    
- lecture_to_page
    
- markdown output writing
    

Success criteria:

- user can paste text and get usable outputs in correct folders
    

## Phase 2 — Notion integration

Deliverables:

- task schema mapping
    
- create tasks in Notion database
    
- robust env/config handling
    
- dry-run mode
    

Success criteria:

- extracted tasks sync correctly to Notion
    

## Phase 3 — Publication pipeline

Deliverables:

- MkDocs config generation
    
- navigation structure by module/week/session
    
- GitHub Actions deploy workflow
    

Success criteria:

- lecture pages are published as book-style site on GitHub Pages
    

## Phase 4 — Thin UI/mobile support

Deliverables:

- basic web UI or documented Obsidian workflow
    
- inbox note creation helpers
    
- optional share-sheet/shortcut documentation
    

## Phase 5 — Extension layer

Possible additions:

- router skill
    
- schedule-aware communications
    
- speaker profile injection
    
- task back-sync from Notion
    
- LMS adapters
    

---

## 16. Detailed UI/UX expectations

### 16.1 V1 may be CLI-first

The fastest build path is CLI plus repo structure.

Example commands:

- `app run-skill meeting_to_actions --input inbox/transcripts/x.md`
    
- `app run-skill email_reply --stdin`
    
- `app run-skill lecture_to_page --input inbox/transcripts/y.md --module AI-CI`
    
- `app publish build`
    

### 16.2 V2 thin web UI

Minimal screens:

- Inbox
    
- Run Skill
    
- Review Output
    
- Publish
    
- Settings
    

#### Inbox screen

- upload/paste text
    
- choose or infer input type
    
- assign metadata like module/week/date
    

#### Skill screen

- choose skill
    
- preview retrieved source docs
    
- run
    

#### Output screen

- show generated markdown / email / tasks
    
- edit before save or sync
    

#### Publish screen

- list publishable session pages
    
- build/deploy site
    

### 16.3 Mobile usage expectation

Target user flow on mobile:

1. paste transcript or email
    
2. select workflow
    
3. review output
    
4. save / sync / publish
    

This must require minimal taps and no manual file path management in normal use.

---

## 17. Notion integration design

### 17.1 Minimal databases

For v1, only one database is required.

#### Programme Tasks

Required properties:

- Title (title)
    
- Description (rich text)
    
- Deadline (date)
    
- Module (select)
    
- Source (url or rich text)
    
- Status (select: todo, doing, done)
    

### 17.2 Sync behaviour

- create tasks by default
    
- optionally deduplicate using title + source file + date
    
- support dry-run mode for testing
    

### 17.3 Config

Use environment variables and/or config file:

- `NOTION_API_KEY`
    
- `NOTION_TASK_DB_ID`
    

---

## 18. Publication design

### 18.1 Desired public structure

Book-style navigation:

- Home
    
- Module
    
    - Week
        
        - Session
            

### 18.2 Folder mapping

Example:

```text
publish/modules/ai-ci/index.md
publish/modules/ai-ci/week-01/session-01.md
publish/modules/ai-ci/week-01/session-02.md
```

### 18.3 Generated nav

Automatically generate MkDocs nav from folder structure and frontmatter titles where possible.

### 18.4 Publication rules

Only files with `publish: true` should be included in site navigation.

---

## 19. Security and privacy

### 19.1 Private vs public content

The system must enforce separation between:

- internal knowledge and meeting notes
    
- public publishable lecture/session pages
    

### 19.2 Do not publish by default

Publication must always be opt-in via frontmatter or explicit route.

### 19.3 Sensitive content

Never expose:

- student personal data
    
- staff HR-like discussions
    
- internal decision notes
    
- confidential emails
    

Developer note: add publication filters and warnings.

---

## 20. Testing requirements

### 20.1 Unit tests

- file path generation
    
- frontmatter parsing
    
- skill loading
    
- retrieval rules
    
- template rendering
    
- Notion payload mapping
    

### 20.2 Integration tests

- run each skill on fixture inputs
    
- verify output files are written correctly
    
- verify structured output validates against schema
    
- mock Notion API calls
    

### 20.3 Fixture set

Create sample fixtures for:

- meeting transcript
    
- lecture transcript
    
- student email
    
- module brief
    
- assessment brief
    
- schedule file
    

---

## 21. Developer ergonomics

### 21.1 Required project docs

Include:

- `README.md` for quick start
    
- `ARCHITECTURE.md`
    
- `SKILLS.md`
    
- `.env.example`
    
- `docs/` for deeper developer notes
    

### 21.2 CLI ergonomics

All key workflows should be runnable from one CLI namespace.

### 21.3 Logging

Provide clear logs for:

- retrieved files
    
- skill chosen
    
- output file created
    
- Notion sync status
    
- publication result
    

---

## 22. Example build tasks for Codex / Claude Code

A coding agent should be instructed to complete the project in the following order.

### Task 1 — Scaffold repo

- create directory structure
    
- create config files
    
- create template files
    
- create sample skill YAML files
    

### Task 2 — Build repository manager

- implement file read/write helpers
    
- implement frontmatter parser
    
- implement path helpers
    

### Task 3 — Build skill loader and runner

- load skill definitions from YAML
    
- support input validation
    
- build context package from retrieval rules
    
- call pluggable LLM backend interface
    

### Task 4 — Implement retrieval engine

- folder-scoped search
    
- metadata filtering
    
- keyword search
    
- recent relevant note lookup
    

### Task 5 — Implement structured schemas

- Pydantic models for outputs
    
- JSON validation
    
- markdown renderers
    

### Task 6 — Implement meeting_to_actions

- prompt template
    
- output validation
    
- markdown writer
    
- task extraction
    

### Task 7 — Implement email_reply

- prompt template
    
- retrieval of relevant docs
    
- output renderer
    

### Task 8 — Implement lecture_to_page

- prompt template
    
- markdown page writer
    
- publish path helper
    

### Task 9 — Implement Notion sync

- config loading
    
- create task API calls
    
- dry run + mock tests
    

### Task 10 — Implement publication pipeline

- MkDocs config
    
- nav generation
    
- GitHub Actions deploy workflow
    

### Task 11 — Implement optional thin UI

- paste/upload text
    
- choose skill
    
- show output
    
- save/sync
    

---

## 23. Non-functional requirements

- must be easy to run locally
    
- must be portable across machines
    
- must degrade gracefully if Notion is disabled
    
- must remain usable as markdown repo even if app layer disappears
    
- must support future extension without deep refactors
    
- must be understandable by another developer within one day
    

---

## 24. Open design decisions

These should be kept configurable rather than hard-coded.

- whether the primary interface is CLI, web UI, or Obsidian-only
    
- whether retrieval remains lexical or adds embeddings
    
- whether Notion is optional or mandatory in deployment
    
- whether publication is pushed automatically or manually approved
    
- whether email sending/Canvas posting is ever automated
    

---

## 25. Recommended v1 success metric

The system is successful if the user can, from a mobile-friendly setup:

- paste a meeting transcript and get a usable summary plus tracked tasks
    
- paste an email and get a grounded reply
    
- paste a lecture transcript and publish a clean public class page
    
- generate a weekly student update grounded in schedule and materials
    

all without needing a heavy or brittle technical workflow.

---

## 26. Suggested README quick start outline

The production repo should include a concise quick start roughly like this:

1. clone repo
    
2. create virtualenv
    
3. install dependencies
    
4. copy `.env.example` to `.env`
    
5. configure Notion credentials if desired
    
6. add source docs under `knowledge/`
    
7. place transcript under `inbox/transcripts/`
    
8. run a skill command
    
9. review generated output
    
10. optionally build/publish site
    

---

## 27. Final recommendation

Build this as a modular Python application over a markdown repository with:

- config-driven skills
    
- schema-validated outputs
    
- minimal Notion integration
    
- MkDocs publication
    
- optional thin web UI later
    

Avoid overengineering. The main innovation is not fancy infrastructure; it is the combination of:

- durable markdown knowledge
    
- grounded AI skills
    
- structured task extraction
    
- clean publish pipeline
    

That should remain the north star throughout implementation.