"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  GraduationCap,
  Layers3,
  LockKeyhole,
  Plus,
  RefreshCw,
  Sparkles,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WebConfig } from "@/lib/config";
import { record, string } from "@/lib/decode";
import {
  errorMessage,
  learnerRequest,
  parseClasses,
  parseCourses,
  parseCurriculum,
  parseDashboard,
  parseOutline,
  parseSession,
  SchoolError,
  schoolRequest,
  type ClassSummary,
  type CourseSummary,
  type Curriculum,
  type Dashboard,
  type Lesson,
  type Outline,
} from "@/lib/school";
import { school as t } from "@/messages/school";
import { ClassDashboard } from "./class-dashboard";
import { SchoolLesson } from "./school-lesson";
import { LibraryAssignment } from "./library-assignment";

type Session = ReturnType<typeof parseSession>;
const working = new Set(["queued", "researching", "indexing", "graph"]);
const blankOutline = (): Outline => ({
  title: "",
  goal: "",
  lessons: [
    { module: "", title: "", goal: "" },
    { module: "", title: "", goal: "" },
  ],
});

export function SchoolWorkspace({ config }: { config: WebConfig }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [tab, setTab] = useState<"courses" | "classes">("courses");
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [classes, setClasses] = useState<ClassSummary[]>([]);
  const [active, setActive] = useState<Curriculum | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [draft, setDraft] = useState<Outline | null>(null);
  const [creating, setCreating] = useState(false);
  const [goal, setGoal] = useState("");
  const [count, setCount] = useState(6);
  const [className, setClassName] = useState("");
  const [courseId, setCourseId] = useState("");
  const [invite, setInvite] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [teacherLink, setTeacherLink] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const teacherKey = useRef("");
  const reloadLists = useCallback(async () => {
    const [c, cl] = await Promise.all([
      schoolRequest<unknown>("curricula"),
      schoolRequest<unknown>("classes"),
    ]);
    setCourses(parseCourses(c));
    setClasses(parseClasses(cl));
  }, []);
  useEffect(() => {
    if (config.mode !== "api") return;
    let cancelled = false;
    async function initialize() {
      try {
        const url = new URL(window.location.href);
        const key = new URLSearchParams(url.hash.slice(1)).get("key") ?? "";
        teacherKey.current = /^[A-Za-z0-9_-]{43}$/.test(key) ? key : "";
        let current: Session | null = null;
        try {
          current = parseSession(await schoolRequest<unknown>("session"));
        } catch (e) {
          if (!(e instanceof SchoolError) || e.status !== 401) throw e;
        }
        if (cancelled) return;
        setSession(current);
        if (current) await reloadLists();
        const classId = url.searchParams.get("class");
        if (classId && (current || teacherKey.current)) {
          const data = parseDashboard(
            await schoolRequest<unknown>(
              `classes/${encodeURIComponent(classId)}`,
              { key: teacherKey.current },
            ),
          );
          if (!cancelled) {
            setDashboard(data);
            setTab("classes");
            if (teacherKey.current) setTeacherLink(window.location.href);
          }
        } else if (current && url.searchParams.get("course")) {
          const data = parseCurriculum(
            await schoolRequest<unknown>(
              `curricula/${encodeURIComponent(url.searchParams.get("course")!)}`,
            ),
          );
          if (!cancelled) {
            setActive(data);
            const item = data.lessons.find(
              (l) => l.id === url.searchParams.get("lesson"),
            );
            if (item && ["ready", "learning", "completed"].includes(item.state))
              setLesson(item);
          }
        }
      } catch (e) {
        if (!cancelled) setError(errorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void initialize();
    return () => {
      cancelled = true;
    };
  }, [config.mode, reloadLists]);
  useEffect(() => {
    if (!active || !active.lessons.some((l) => working.has(l.state))) return;
    const controller = new AbortController();
    const id = active.id;
    const timer = setInterval(() => {
      schoolRequest<unknown>(`curricula/${id}`, { signal: controller.signal })
        .then(parseCurriculum)
        .then((data) => {
          setActive((current) => (current?.id === id ? data : current));
        })
        .catch((e) => {
          if (!controller.signal.aborted) setError(errorMessage(e));
        });
    }, 4000);
    return () => {
      clearInterval(timer);
      controller.abort();
    };
  }, [active]);

  async function run(action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function home(next: "courses" | "classes") {
    setTab(next);
    setActive(null);
    setLesson(null);
    setDashboard(null);
    setCreating(false);
    setDraft(null);
    setError("");
    history.replaceState(null, "", "/school");
  }
  async function openCourse(id: string) {
    const data = parseCurriculum(
      await schoolRequest<unknown>(`curricula/${id}`),
    );
    setActive(data);
    setLesson(null);
    setDashboard(null);
    setCreating(false);
    setDraft(null);
    setTab("courses");
    history.replaceState(null, "", `/school?course=${id}`);
  }
  async function openClass(id: string, key = "") {
    const data = parseDashboard(
      await schoolRequest<unknown>(`classes/${id}`, { key }),
    );
    teacherKey.current = key;
    setDashboard(data);
    setActive(null);
    setLesson(null);
    setTab("classes");
    const path = `/school?class=${id}${key ? `#key=${key}` : ""}`;
    history.replaceState(null, "", path);
    setTeacherLink(key ? new URL(path, window.location.origin).href : "");
  }
  async function refreshProgress() {
    if (!active || !lesson) return false;
    const data = parseCurriculum(
      await schoolRequest<unknown>(`curricula/${active.id}`),
    );
    setActive(data);
    return data.lessons.find((l) => l.id === lesson.id)?.state === "completed";
  }
  function changeLesson(
    index: number,
    field: "module" | "title" | "goal",
    value: string,
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            lessons: current.lessons.map((l, i) =>
              i === index ? { ...l, [field]: value } : l,
            ),
          }
        : null,
    );
  }

  return (
    <div className="school">
      <a href="#school-main" className="school-skip">
        {t.curriculum}
      </a>
      <header className="school-topbar">
        <Link href="/school" className="school-brand">
          <GraduationCap size={26} aria-hidden="true" />
          {t.app}
          <span>
            {t.curriculum} & {t.classroom}
          </span>
        </Link>
        <Link href="/">
          {t.home}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </header>
      <div className="school-shell">
        <aside className="school-nav">
          <p className="school-eyebrow">{t.app}</p>
          <button
            aria-current={tab === "courses" ? "page" : undefined}
            onClick={() => home("courses")}
          >
            <Layers3 size={19} aria-hidden="true" />
            {t.curriculum}
          </button>
          <button
            aria-current={tab === "classes" ? "page" : undefined}
            onClick={() => home("classes")}
          >
            <Users size={19} aria-hidden="true" />
            {t.classroom}
          </button>
          {session && (
            <div className="school-profile">
              <span>{session.name.slice(0, 1).toLocaleUpperCase("vi")}</span>
              <div>
                <strong>{session.name}</strong>
                <small>{t.profile}</small>
              </div>
            </div>
          )}
        </aside>
        <main id="school-main" className="school-main" tabIndex={-1}>
          {config.mode !== "api" ? (
            <p className="school-error" role="alert">
              {t.apiOnly}
            </p>
          ) : loading ? (
            <p role="status">{t.loading}</p>
          ) : (
            <>
              {error && (
                <p className="school-error" role="alert">
                  {error}
                </p>
              )}
              {dashboard ? (
                <ClassDashboard
                  data={dashboard}
                  teacherLink={teacherLink}
                  busy={busy}
                  refresh={() =>
                    run(() => openClass(dashboard.id, teacherKey.current))
                  }
                  back={() => home("classes")}
                />
              ) : !session ? (
                <section className="school-panel school-login">
                  <GraduationCap size={38} aria-hidden="true" />
                  <h1>{t.profile}</h1>
                  <p>{t.sessionHint}</p>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void run(async () => {
                        await learnerRequest("learners", {
                          display_name: name,
                        });
                        setSession(
                          parseSession(await schoolRequest<unknown>("session")),
                        );
                        await reloadLists();
                      });
                    }}
                  >
                    <label htmlFor="school-name">{t.name}</label>
                    <input
                      id="school-name"
                      required
                      maxLength={80}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                    <Button type="submit" disabled={busy || !name.trim()}>
                      {busy ? t.loading : t.enter}
                    </Button>
                  </form>
                </section>
              ) : lesson && active ? (
                <SchoolLesson
                  key={lesson.id}
                  course={active.id}
                  lesson={lesson}
                  learner={session.learner_id}
                  config={config}
                  back={() => run(() => openCourse(active.id))}
                  progress={refreshProgress}
                />
              ) : active ? (
                <>
                  <div className="school-actions school-between">
                    <Button variant="ghost" onClick={() => home("courses")}>
                      <ArrowLeft size={16} aria-hidden="true" />
                      {t.back}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy}
                      onClick={() => run(() => openCourse(active.id))}
                    >
                      <RefreshCw size={16} aria-hidden="true" />
                      {t.refresh}
                    </Button>
                  </div>
                  <div className="school-course-hero">
                    <span className="school-eyebrow">{t.curriculum}</span>
                    <h1>{active.title}</h1>
                    <p>{active.goal}</p>
                    <div className="school-course-progress">
                      <progress
                        value={active.completed}
                        max={active.lessons.length}
                      />
                      <span>
                        {active.completed}/{active.lessons.length} {t.progress}
                      </span>
                    </div>
                  </div>
                  <p className="school-sequence">{t.sequence}</p>
                  <ol className="school-lessons">
                    {active.lessons.map((entry) => (
                      <li
                        className={`school-lesson-card ${entry.state}`}
                        key={entry.id}
                      >
                        <div className="school-lesson-number">
                          {entry.state === "completed" ? (
                            <CheckCircle2
                              size={24}
                              aria-label={t.states.completed}
                            />
                          ) : entry.state === "locked" ? (
                            <LockKeyhole
                              size={20}
                              aria-label={t.states.locked}
                            />
                          ) : (
                            String(entry.position).padStart(2, "0")
                          )}
                        </div>
                        <div className="school-lesson-info">
                          <span className="school-eyebrow">{entry.module}</span>
                          <h2>{entry.title}</h2>
                          <p>{entry.goal}</p>
                          <div className="school-lesson-meta">
                            <span className={`school-badge ${entry.state}`}>
                              {t.states[entry.state]}
                            </span>
                            {entry.concepts > 0 && (
                              <span>
                                {entry.mastered}/{entry.concepts} {t.mastered}
                              </span>
                            )}
                          </div>
                          {working.has(entry.state) && (
                            <p role="status">{entry.step_vi}</p>
                          )}
                          {entry.state === "failed" && (
                            <p className="school-inline-error">
                              {entry.step_vi}
                            </p>
                          )}
                          {entry.material_goal && (
                            <p className="school-material-goal">
                              <strong>{t.materialGoal}: </strong>
                              {entry.material_goal}
                            </p>
                          )}
                          {active.can_manage &&
                            ["locked", "not_started", "failed"].includes(
                              entry.state,
                            ) && (
                              <LibraryAssignment
                                course={active.id}
                                lesson={entry.id}
                                refresh={() => openCourse(active.id)}
                              />
                            )}
                        </div>
                        <Button
                          variant={
                            entry.state === "completed"
                              ? "secondary"
                              : "primary"
                          }
                          disabled={
                            busy ||
                            entry.state === "locked" ||
                            working.has(entry.state)
                          }
                          onClick={() =>
                            run(async () => {
                              if (
                                ["ready", "learning", "completed"].includes(
                                  entry.state,
                                )
                              ) {
                                setLesson(entry);
                                history.replaceState(
                                  null,
                                  "",
                                  `/school?course=${active.id}&lesson=${entry.id}`,
                                );
                              } else {
                                await schoolRequest(
                                  `curricula/${active.id}/lessons/${entry.id}/start`,
                                  { body: { retry: entry.state === "failed" } },
                                );
                                await openCourse(active.id);
                              }
                            })
                          }
                        >
                          {entry.state === "locked"
                            ? t.states.locked
                            : entry.state === "failed"
                              ? t.retry
                              : ["ready", "learning", "completed"].includes(
                                    entry.state,
                                  )
                                ? t.open
                                : working.has(entry.state)
                                  ? t.loading
                                  : t.start}
                        </Button>
                      </li>
                    ))}
                  </ol>
                </>
              ) : tab === "courses" ? (
                <>
                  <div className="school-section-heading">
                    <div>
                      <span className="school-eyebrow">{t.curriculum}</span>
                      <h1>{t.heading}</h1>
                      <p>{t.subtitle}</p>
                    </div>
                    <Button
                      onClick={() => {
                        setCreating(true);
                        setDraft(null);
                      }}
                    >
                      <Plus size={17} aria-hidden="true" />
                      {t.create}
                    </Button>
                  </div>
                  {creating && (
                    <section className="school-panel">
                      <h2>{t.create}</h2>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            setDraft(
                              parseOutline(
                                await schoolRequest<unknown>(
                                  "curricula/outline",
                                  { body: { goal, lesson_count: count } },
                                ),
                              ),
                            );
                          });
                        }}
                        className="school-plan-form"
                      >
                        <label>
                          {t.goal}
                          <textarea
                            required
                            minLength={10}
                            maxLength={500}
                            value={goal}
                            onChange={(e) => setGoal(e.target.value)}
                            placeholder={t.goalPlaceholder}
                          />
                        </label>
                        <label>
                          {t.count}
                          <select
                            aria-label={t.count}
                            value={count}
                            onChange={(e) => setCount(Number(e.target.value))}
                          >
                            {Array.from(
                              { length: 11 },
                              (_, index) => index + 2,
                            ).map((n) => (
                              <option key={n} value={n}>
                                {n}
                              </option>
                            ))}
                          </select>
                        </label>
                        <Button
                          type="submit"
                          disabled={busy || goal.trim().length < 10}
                        >
                          <Sparkles size={16} aria-hidden="true" />
                          {busy ? t.loading : t.plan}
                        </Button>
                        <Button
                          variant="ghost"
                          disabled={busy}
                          onClick={() => {
                            setDraft({ ...blankOutline(), goal });
                          }}
                        >
                          {t.manual}
                        </Button>
                      </form>
                    </section>
                  )}
                  {draft && (
                    <section className="school-panel">
                      <div className="school-section-heading">
                        <div>
                          <h2>{t.draft}</h2>
                          <p>{t.draftHint}</p>
                        </div>
                      </div>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            const created = record(
                              await schoolRequest<unknown>("curricula", {
                                body: draft,
                              }),
                            );
                            await reloadLists();
                            await openCourse(string(created.id));
                          });
                        }}
                      >
                        <label>
                          {t.title}
                          <input
                            required
                            maxLength={160}
                            value={draft.title}
                            onChange={(e) =>
                              setDraft({ ...draft, title: e.target.value })
                            }
                          />
                        </label>
                        <label>
                          {t.goal}
                          <textarea
                            required
                            minLength={10}
                            maxLength={500}
                            value={draft.goal}
                            onChange={(e) =>
                              setDraft({ ...draft, goal: e.target.value })
                            }
                          />
                        </label>
                        <div className="school-draft-lessons">
                          {draft.lessons.map((entry, i) => (
                            <fieldset key={i}>
                              <legend>
                                {t.lesson} {i + 1}
                              </legend>
                              <label>
                                {t.module}
                                <input
                                  required
                                  maxLength={100}
                                  value={entry.module}
                                  onChange={(e) =>
                                    changeLesson(i, "module", e.target.value)
                                  }
                                />
                              </label>
                              <label>
                                {t.lessonTitle}
                                <input
                                  required
                                  maxLength={160}
                                  value={entry.title}
                                  onChange={(e) =>
                                    changeLesson(i, "title", e.target.value)
                                  }
                                />
                              </label>
                              <label>
                                {t.lessonGoal}
                                <textarea
                                  required
                                  minLength={10}
                                  maxLength={500}
                                  value={entry.goal}
                                  onChange={(e) =>
                                    changeLesson(i, "goal", e.target.value)
                                  }
                                />
                              </label>
                              <Button
                                variant="ghost"
                                disabled={draft.lessons.length <= 2}
                                onClick={() =>
                                  setDraft({
                                    ...draft,
                                    lessons: draft.lessons.filter(
                                      (_, index) => index !== i,
                                    ),
                                  })
                                }
                              >
                                {t.remove}
                              </Button>
                            </fieldset>
                          ))}
                        </div>
                        <div className="school-actions">
                          <Button type="submit" disabled={busy}>
                            {busy ? t.loading : t.save}
                          </Button>
                          <Button
                            variant="secondary"
                            disabled={draft.lessons.length >= 12 || busy}
                            onClick={() =>
                              setDraft({
                                ...draft,
                                lessons: [
                                  ...draft.lessons,
                                  { module: "", title: "", goal: "" },
                                ],
                              })
                            }
                          >
                            <Plus size={16} aria-hidden="true" />
                            {t.addLesson}
                          </Button>
                        </div>
                      </form>
                    </section>
                  )}
                  {!courses.length && !creating ? (
                    <div className="school-empty">
                      <BookOpen size={38} aria-hidden="true" />
                      <p>{t.emptyCourses}</p>
                    </div>
                  ) : (
                    <div className="school-course-grid">
                      {courses.map((course) => (
                        <button
                          className="school-course-card"
                          key={course.id}
                          onClick={() => run(() => openCourse(course.id))}
                        >
                          <span className="school-course-icon">
                            <BookOpen size={23} aria-hidden="true" />
                          </span>
                          <h2>{course.title}</h2>
                          <p>{course.goal}</p>
                          <span>
                            {course.lesson_count}{" "}
                            {t.lesson.toLocaleLowerCase("vi")}
                            <ArrowRight size={17} aria-hidden="true" />
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="school-section-heading">
                    <div>
                      <span className="school-eyebrow">{t.classroom}</span>
                      <h1>{t.classes}</h1>
                      <p>{t.subtitle}</p>
                    </div>
                    <Users size={32} aria-hidden="true" />
                  </div>
                  <div className="school-class-forms">
                    <section className="school-panel">
                      <h2>{t.createClass}</h2>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            const value = record(
                              await schoolRequest<unknown>("classes", {
                                body: {
                                  name: className,
                                  curriculum_id: courseId || courses[0]?.id,
                                },
                              }),
                            );
                            await reloadLists();
                            await openClass(
                              string(value.id),
                              string(value.teacher_key),
                            );
                          });
                        }}
                      >
                        <label>
                          {t.className}
                          <input
                            required
                            maxLength={120}
                            value={className}
                            onChange={(e) => setClassName(e.target.value)}
                          />
                        </label>
                        <label>
                          {t.chooseCourse}
                          <select
                            aria-label={t.chooseCourse}
                            required
                            value={courseId || courses[0]?.id || ""}
                            onChange={(e) => setCourseId(e.target.value)}
                          >
                            <option value="" disabled>
                              {t.chooseCourse}
                            </option>
                            {courses.map((course) => (
                              <option value={course.id} key={course.id}>
                                {course.title}
                              </option>
                            ))}
                          </select>
                        </label>
                        <Button
                          type="submit"
                          disabled={
                            busy || !courses.length || !className.trim()
                          }
                        >
                          {t.createClass}
                        </Button>
                      </form>
                    </section>
                    <section className="school-panel">
                      <h2>{t.join}</h2>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          void run(async () => {
                            const value = record(
                              await schoolRequest<unknown>("classes/join", {
                                body: { invite_code: invite.trim() },
                              }),
                            );
                            await reloadLists();
                            await openCourse(string(value.curriculum_id));
                          });
                        }}
                      >
                        <label>
                          {t.invite}
                          <input
                            required
                            minLength={16}
                            maxLength={16}
                            autoComplete="off"
                            value={invite}
                            onChange={(e) => setInvite(e.target.value)}
                            placeholder={t.invitePlaceholder}
                          />
                        </label>
                        <Button
                          type="submit"
                          disabled={busy || invite.trim().length !== 16}
                        >
                          {t.join}
                        </Button>
                      </form>
                    </section>
                  </div>
                  {!classes.length ? (
                    <p className="school-empty">{t.emptyClasses}</p>
                  ) : (
                    <div className="school-course-grid">
                      {classes.map((entry) => (
                        <button
                          className="school-course-card"
                          key={entry.id}
                          onClick={() =>
                            run(() =>
                              entry.role === "teacher"
                                ? openClass(entry.id)
                                : openCourse(entry.curriculum_id),
                            )
                          }
                        >
                          <span className="school-badge">
                            {entry.role === "teacher" ? t.teacher : t.student}
                          </span>
                          <h2>{entry.name}</h2>
                          <p>{entry.curriculum_title}</p>
                          <span>
                            {entry.role === "teacher" ? t.dashboard : t.open}
                            <ArrowRight size={17} aria-hidden="true" />
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
