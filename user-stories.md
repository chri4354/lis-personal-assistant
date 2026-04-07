# 🧠 Core User Stories — personal-assistant

## 1. Capture & Input (mobile-first)

### 1. Meeting transcript ingestion

**As a user**, I want to paste a meeting transcript into the app, select a “meeting” agent, and generate structured outputs (summary + actions), so that I can quickly capture and operationalise meetings.

---

### 2. Voice note → transcript → processing

**As a user**, I want to record a voice note on my iPhone, convert it to text, paste it into the app, and process it with an agent, so that I can capture ideas and meetings on the go.

---

### 3. Email ingestion

**As a user**, I want to paste an incoming email into the app and select an “email reply” agent, so that I can quickly draft a context-aware response.

---

### 4. Lecture transcript ingestion

**As a user**, I want to paste a lecture transcript into the app and generate a structured lecture summary, so that I can create reusable teaching materials.

---

### 5. Quick capture (unstructured notes)

**As a user**, I want to quickly dump unstructured notes into an inbox, so that I don’t lose ideas even when I don’t process them immediately.

---

## 2. Skill Execution (core of the system)

### 6. Select and run a skill

**As a user**, I want to select a predefined agent/skill (e.g. meeting, email, lecture), so that I can apply the correct transformation to my input.

---

### 7. Skill auto-detection (v2)

**As a user**, I want the system to suggest the appropriate skill based on my input, so that I don’t need to choose manually every time.

---

### 8. Grounded processing

**As a user**, I want the system to use internal documents (assessment briefs, module info) when generating outputs, so that responses are accurate and consistent.

---

### 9. Output preview and editing

**As a user**, I want to review and edit the generated output before saving or sending, so that I maintain control over final content.

---

## 3. Task Management & Notion Integration

### 10. Extract tasks from meetings

**As a user**, I want meeting transcripts to be converted into structured tasks, so that actions are not lost.

---

### 11. Push tasks to Notion

**As a user**, I want extracted tasks to be automatically added to my Notion task database, so that I can track and manage them.

---

### 12. Task structure enforcement

**As a user**, I want tasks to include title, description, deadline (if present), and source, so that they are usable in my workflow.

---

### 13. Traceability

**As a user**, I want each task to link back to the source meeting or note, so that I can understand context later.

---

## 4. Communication & Coordination

### 14. Draft email replies

**As a user**, I want to generate email drafts grounded in programme documents, so that I can respond quickly and consistently.

---

### 15. Generate weekly student updates

**As a user**, I want to generate weekly communications summarising past sessions and upcoming work, so that students stay aligned.

---

### 16. Generate announcements (Canvas-ready)

**As a user**, I want to create structured announcements based on module content and schedule, so that I can easily communicate with students.

---

### 17. Speaker introduction generation

**As a user**, I want to generate short bios or introductions for guest speakers, so that I can include them in communications.

---

## 5. Knowledge Management (Obsidian / Markdown)

### 18. Store structured outputs

**As a user**, I want all processed outputs (meetings, lectures, comms) saved as markdown files, so that I have a durable knowledge base.

---

### 19. Organise by module / week / session

**As a user**, I want content organised hierarchically (module → week → session), so that I can easily navigate materials.

---

### 20. Search across knowledge

**As a user**, I want to search across all notes and outputs, so that I can retrieve past decisions and materials quickly.

---

## 6. Publishing (GitHub Pages “book”)

### 21. Generate lecture pages

**As a user**, I want lecture summaries converted into clean, structured pages, so that they can be shared with students.

---

### 22. Publish course content as a book

**As a user**, I want to publish lecture pages into a GitHub Pages site structured as a course book, so that students can browse materials.

---

### 23. Control what is public vs private

**As a user**, I want to decide which notes are published, so that internal content remains private.

---

## 7. Workflow & Automation

### 24. One-step workflow execution

**As a user**, I want to paste input, select a skill, and get outputs in one step, so that the system remains fast and usable.

---

### 25. Minimal friction on mobile

**As a user**, I want to perform all core actions (capture, process, save) from my phone in under a minute, so that I actually use the system daily.

---

### 26. Reusable templates

**As a user**, I want outputs to follow consistent templates, so that content is structured but not rigid.

---

### 27. Extend with new skills

**As a user/developer**, I want to add new skills without changing the core system, so that the app can evolve over time.

---

## 8. Reliability & Trust

### 28. No hallucinated policies

**As a user**, I want the system to avoid inventing rules or deadlines, so that I can trust outputs.

---

### 29. Clear uncertainty handling

**As a user**, I want the system to flag uncertainty when information is missing, so that I can make informed decisions.

---

### 30. Deterministic outputs where needed

**As a user**, I want structured outputs (tasks, summaries) to follow predictable formats, so that they integrate with other tools.
