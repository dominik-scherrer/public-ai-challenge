# Deferred work and validation

- A second German-speaking municipality was part of the original MVP acceptance
  plan, but the current crawler permits only `www.ausserberg.ch`. Expanding that
  boundary requires explicit authorization and code changes. No second-site
  result is established by the repository.
- Generated-package Docker build and launch have not been verified locally in
  the recorded review. The builder runs offline subprocess conformance; that is
  distinct from container validation.
- Live model output still needs source spot-checking for any demonstrated
  municipality. Deterministic tests and semantic review cannot establish
  factual accuracy on their own.
- PDF/iCalendar parsing, JavaScript rendering, form submissions, runtime
  refresh, and public hosting/authentication remain outside the implemented
  read-only HTML snapshot workflow.

The implemented commands, boundaries, and tool behavior are documented in
[README.md](README.md). The original design context is summarized in
[ideas-patrick/hackathon-mvp-plan.md](ideas-patrick/hackathon-mvp-plan.md).
