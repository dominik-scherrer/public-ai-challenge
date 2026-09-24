# Ausserberg example: historical design notes

The early concept used Ausserberg to illustrate four possible municipal service
shapes: HTML information, web forms, linked documents, and external portals.
Those categories helped motivate one evidence-backed inventory with explicit
handoffs and gaps.

The earlier examples proposed submissions, PDF interpretation, facility booking,
notices, and a generic multi-municipality adapter. These are ideas, not current
factory capabilities. The implemented package has six fixed read-only tools;
its crawler inspects permitted HTML and explicitly linked public JSON on
`www.ausserberg.ch`, retains document links without parsing their contents, and
never submits forms. See [README.md](../README.md) for the exact tool surface.

This repository does not establish that any particular Ausserberg page, form,
price, procedure, or deadline is current. A generated discovery report contains
the retained excerpts and retrieval times for a specific run; verify decisions
against the official source before relying on them.
