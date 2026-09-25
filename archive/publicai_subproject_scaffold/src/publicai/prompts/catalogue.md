CATALOGUE CONTRACT 1.0
Return all six identifiers exactly: office_hours, garbage_collection, recycling,
move_in, move_out, problem_reporting.

Minimum structured coverage for supported:
- office_hours: a named office with explicit hours (including an explicit
  appointment-only policy if published) AND a contact channel.
- garbage_collection: at least one waste type with actionable collection
  instructions. Dated entries are optional.
- recycling: at least one material with an explicit disposal route or point.
  Store the disposal route in entries[].instructions or the disposal point in
  entries[].locations, with supporting evidence. A collection-point name in
  label alone, even alongside materials and hours, does not satisfy the
  structured minimum; that inventory remains partial. Review coverage against
  the populated structured fields, not information left only in labels or sources.
- move_in: explicit registration guidance AND an official contact or registration
  destination. A page/form title alone is a service handoff, not guidance.
- move_out: explicit deregistration guidance AND an official contact or
  deregistration destination. Form labels alone are not procedural requirements.
- problem_reporting: an explicitly documented reporting channel AND its stated
  purpose. A general contact address alone is insufficient.

Coverage partial: substantive cited data below minimum or unresolved conflicts.
Coverage handoff_only: specific official destination without usable guidance.
Coverage unavailable: neither structured guidance nor a specific handoff found.

Conflicts preserve evidence-backed alternatives only in conflicts, never in
entries or definitive validity dates. Such retained alternatives may pass review
with status conflicting if each excerpt really supports the stated alternative;
unresolved conflicts do not by themselves forbid a partial package. Do not set
blocking issues for faithfully reported gaps or these retained alternatives.

Coverage metadata must reflect actual discovered facts. zone_required requires
published zone dependence; never invent geographic mappings. limitations and
missing_reasons describe acquisition/coverage gaps only, never add municipal
facts outside evidence-backed fields. explicitly_not_offered is allowed only if
the cited text directly says so. Treat empty data as unknown, not not-offered.
Review these metadata paths as carefully as facts. Published date validity must
explicitly establish complete interval coverage; first/last observed dates do not.
