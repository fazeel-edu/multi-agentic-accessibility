# Pinned versions

Verified against PyPI on 2026-11-21 (re-verify at each pin change).

| Package | Pin | Latest on PyPI |
| --- | --- | --- |
| Python | 3.12 | n/a |
| claude-agent-sdk | >=0.2.177,<0.3 (needs hook `on_failure`) | 0.2.187 |
| playwright | ==1.65.2 | 1.65.2 |
| pydantic | ==2.14.4 | 2.14.4 |
| fastapi | ==0.165.0 | 0.165.0 |
| jinja2 | >=3.1.6 | 3.1.6 |
| lxml | ==6.1.3 (pinned HTML parser for element keys, AD-15) | 6.1.3 |
| cssselect | ==1.6.0 (CSS to XPath for element keys) | 1.6.0 |
| pytest (dev) | >=9.2 | 9.2.0 |
| ruff (dev) | >=0.17 | 0.17.6 |

Exact resolved versions are in `uv.lock`. axe-core 4.14.1 is vendored in `vendor/axe-core/` (MPL-2.0, licence beside it), taken from the npm tarball `axe-core-4.14.1.tgz` on 2026-11-21 (npm `version` field 4.14.1). Chromium: Playwright 1.65.2 build `chromium-headless-shell` v1255 (Chrome 159).
