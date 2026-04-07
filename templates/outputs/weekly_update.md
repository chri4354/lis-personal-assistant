---
title: "{{ data.subject }}"
type: weekly-communication
{% if metadata and metadata.module %}module: "{{ metadata.module }}"{% endif %}
{% if metadata and metadata.week %}week: {{ metadata.week }}{% endif %}
date: {{ today }}
status: draft
---

# {{ data.subject }}

{{ data.body }}

{% if data.deadlines_mentioned %}
---
**Key Deadlines:**
{% for deadline in data.deadlines_mentioned %}
- {{ deadline }}
{% endfor %}
{% endif %}
