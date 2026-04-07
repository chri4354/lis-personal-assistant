---
title: "{{ data.title }}"
type: lecture-summary
{% if metadata and metadata.module %}module: "{{ metadata.module }}"{% endif %}
{% if metadata and metadata.module_code %}module_code: "{{ metadata.module_code }}"{% endif %}
{% if metadata and metadata.date %}date: {{ metadata.date }}{% endif %}
{% if metadata and metadata.week %}week: {{ metadata.week }}{% endif %}
{% if metadata and metadata.session %}session: {{ metadata.session }}{% endif %}
status: draft
publish: false
source_files:
  - "{{ source_file }}"
---

# {{ data.title }}

## Overview

{{ data.overview }}

## Key Concepts

{% for concept in data.key_concepts %}
- {{ concept }}
{% endfor %}

## Examples & Case Studies

{% for example in data.examples %}
- {{ example }}
{% endfor %}
{% if not data.examples %}
_No specific examples discussed._
{% endif %}

## Questions Raised

{% for question in data.questions_raised %}
- {{ question }}
{% endfor %}
{% if not data.questions_raised %}
_No questions recorded._
{% endif %}

## Clarifications

{% for clarification in data.clarifications %}
- {{ clarification }}
{% endfor %}
{% if not data.clarifications %}
_No clarifications needed._
{% endif %}

## Further Reading

{% for reading in data.further_reading %}
- {{ reading }}
{% endfor %}
{% if not data.further_reading %}
_No further reading suggested._
{% endif %}
