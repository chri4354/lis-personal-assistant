---
title: "{{ data.subject_suggestion }}"
type: email-draft
date: {{ today }}
status: draft
source_files:
  - "{{ source_file }}"
grounding_sources:
{% for src in data.grounding_sources %}
  - "{{ src }}"
{% endfor %}
---

# Email Draft: {{ data.subject_suggestion }}

## Reply Body

{{ data.body }}

{% if data.warnings %}
## Warnings

{% for warning in data.warnings %}
- ⚠ {{ warning }}
{% endfor %}
{% endif %}

## Sources Used

{% for src in data.grounding_sources %}
- `{{ src }}`
{% endfor %}
