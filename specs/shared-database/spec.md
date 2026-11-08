# Shared database integration

All local team components use the repository-root `.env` and one `DATABASE_URL`.
P1 retrieval/learning, P2 storage/sessions, P3 jobs and P4 content use the same
PostgreSQL relations. P5 accesses those records through the authenticated API.
Existing learner and source data must be preserved; test databases remain isolated.

Acceptance: every runtime entry point honors the shared settings; the integration
check covers each team's tables and all canonical migrations; the web preserves
review selection parameters; the configured database passes a read-only audit.
