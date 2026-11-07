# Integration boundaries

Branch `p5-curriculum-class` starts at `34383cc`. The research/question work can
continue independently: this feature does not edit research, content generation,
verification, engine or worker modules.

- New backend: `apps/api/app/school/`. `School` reads the existing graph, mastery,
  attempts and confirmation records and writes only course/class membership and
  lesson/topic associations. API identity reuses `LearnerSessions`.
- New entry point: `app.school.main:create_school_app` wraps the existing content
  app and mounts `/school/*`. Existing deployments keep working with their old
  factory; switch the factory when integrating the new routes.
- Additive migrations `0014_curriculum_classroom.sql` and
  `0015_curriculum_content_unique.sql` create course/class tables and enforce one
  occurrence of a topic per course. No existing learning data is rewritten.
- New web route `/school`, separate same-origin `/api/school/*` proxy, scoped CSS
  and Vietnamese messages. Existing components, source links and public-item
  decoders are reused.
- Shared frontend integration edits are limited to the existing proxy and its
  regression tests, plus learner-session reuse in the existing data client:
  allow `/next-item` and compare Origin with the browser-facing
  Host rather than Next's internal `0.0.0.0` bind address. Foreign origins are
  still rejected. Neither proxy exposes the server API key.
  Returning to the original learning page reuses the current school session
  rather than replacing a class member with a new anonymous learner. Older APIs
  without the school route retain their previous learner-creation behavior.

The new page preserves NodeTrail's forest/paper colors and existing controls.
Responsive tables have a labelled scroll region, forms have visible labels,
state indicators include text, and reduced-motion preferences are supported.

## Validation

Use real PostgreSQL integration tests in a module-isolated migrated database.
Keep fake model/publication fixtures confined to tests. Test authentication,
cross-class isolation, explicit retry, concurrency, revision-aware progression
and current verification of assigned material. Run the complete backend/web
regressions, lint, type checking and production build, then exercise actual
teacher/student sessions in headless system Chrome.
