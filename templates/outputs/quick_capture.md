---
title: "{{ data.summary }}"
type: quick-capture
date: {{ metadata.date or "unknown" }}
status: draft
{% if source_file %}source_files:
  - "{{ source_file }}"{% endif %}
---

# Quick Capture

**{{ data.summary }}**

## Tasks

| Task | Description | Assignee | Deadline | Module | Status |
|------|-------------|----------|----------|--------|--------|
{% for action in data.actions %}
| {{ action.title }} | {{ action.description or "—" }} | {{ action.assignee or "—" }} | {{ action.deadline or "—" }} | {{ action.module or "—" }} | {{ action.status }} |
{% endfor %}
{% if not data.actions %}
| _No tasks extracted._ | | | | | |
{% endif %}
