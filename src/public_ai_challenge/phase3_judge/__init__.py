"""The MMP Judge: the quality gate defined in docs/architecture/adr/0004 and 0007.

Three independent checks, each a pass/fail/withhold verdict — never a
holistic quality score:

- provenance  (schemas.py / provenance in llm.py via rubrics/provenance_judge.yml)
  Does the source evidence actually support this claim?
- injection   (injection.py)
  Does a free-text field carry an instruction to a model, a non-municipality
  link, or payment details? Deterministic checks first, LLM as a second pass.
- coverage    (coverage.py)
  How much of the expected service set did this Build actually produce?
  Feeds the Build Floor decision (ADR-0004).

See pipeline/judge/README.md before changing any of this.
"""
