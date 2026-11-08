# Plan

Use the existing `Settings`, connection pools and `supabase/migrations` as the
canonical configuration and schema. Fix the legacy P4 factory's configuration
bypass. Add a read-only database diagnostic used by the shared launcher, checking
team tables, migration history and embedding storage. Update setup documentation
and the web proxy. Verify against the configured local database and isolated test
databases. No data copying, reseeding or database reset is needed.
