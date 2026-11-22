---
title: 'Story 2.4: Provider terms gate'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.4.

## Implementation Notes

- `config/provider_terms.md` is an undated template (all TODO). `store/terms.py` `require_provider_terms()` returns the ISO `Read on` date or raises `ProviderTermsError` naming what is missing (date, or any of data retention, training use, zero data retention); future and invalid dates are refused. The date goes into `Run.provider_terms_date`.
- Fazeel must read the provider's terms and fill the file in; nothing here asserts what the terms say.
- The gate is called when an LLM Run starts (Story 2.9).
