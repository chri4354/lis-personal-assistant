---
title: "{{ data.title }}"
type: meeting-summary
date: {{ data.date or "unknown" }}
{% if metadata and metadata.module -%}
module: "{{ metadata.module }}"
{% endif -%}
{% if metadata and metadata.module_code -%}
module_code: "{{ metadata.module_code }}"
{% endif -%}
status: draft
source_files:
  - "{{ source_file }}"
---

# {{ data.title }}

**Date:** {{ data.date or "Not specified" }}

## Summary

{% for point in data.summary %}
- {{ point }}
{% endfor %}

## Decisions

{% for decision in data.decisions %}
- {{ decision }}
{% endfor %}
{% if not data.decisions %}
_No decisions recorded._
{% endif %}

## Action Points

| Task | Assignee | Deadline | Module | Status |
|------|----------|----------|--------|--------|
{% for action in data.actions %}
| {{ action.title }} | {{ action.assignee or "—" }} | {{ action.deadline or "—" }} | {{ action.module or "—" }} | {{ action.status }} |
{% endfor %}
{% if not data.actions %}
| _No actions extracted._ | | | | |
{% endif %}

## Open Questions

{% for question in data.open_questions %}
- {{ question }}
{% endfor %}
{% if not data.open_questions %}
_No open questions._
{% endif %}
