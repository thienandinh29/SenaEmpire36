# Curriculum and classroom demo

The learner can build an editable course outline, work through several lessons,
and keep progress after refresh. A lecturer can assign that course to a class and
see actual learner progress and concepts needing support.

## Course acceptance

- A goal produces an editable Vietnamese outline of 2–12 distinct ordered lessons.
  The outline is explicitly a plan, requiring approval before persistence.
- Each lesson has its own narrow goal and module. Starting it uses the existing
  Deep/Pro queue and worker. Concurrent students share one topic job per lesson.
- Research/question failures remain failures. Retrying is explicit and bounded
  by the existing worker; the curriculum never writes a topic's ready flags.
- The course owner can instead select an existing public-web lesson. Assignment
  rechecks current independent verification, at least six questions and current
  graph coverage. Private uploads, duplicate topics in a course and replacement
  of an active lesson are rejected. The selected material's actual scope is shown.
- Completion requires all current graph concepts at BKT mastery ≥0.95 plus the
  learner's confirmation of the current graph revision. Completion is derived,
  not a user-supplied checkbox. Each preceding lesson must be complete to unlock
  the next. The existing learning engine controls placement/practice within a lesson.

## Class acceptance

- The course owner creates a class and receives a student invite code and a
  private teacher link. The teacher key is stored hashed and returned only once.
- Joining uses the existing HttpOnly learner credential, never a caller-supplied
  learner ID. Membership grants course access, not access to the class roster.
- The roster reports lesson completion, assessed concept count, mean recorded
  mastery, attempt count, correct rate and per-lesson states for enrolled members.
- Weak concepts use the engine's threshold (p_known <0.5). Unassessed learners
  remain separate from assessed low mastery. No artificial student data appears
  in the product. The demo class cap is 200 members.

This is a demo access model based on anonymous browser sessions and a private
read capability, not institutional accounts. Educational correctness, arbitrary
subject coverage and production deployment require separate acceptance.
