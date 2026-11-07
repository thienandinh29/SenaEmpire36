import { school as t } from "@/messages/school";
import { DataError } from "./decode";

export type LessonState = keyof typeof t.states;
export interface LessonDraft {
  module: string;
  title: string;
  goal: string;
}
export interface Outline {
  title: string;
  goal: string;
  lessons: LessonDraft[];
}
export interface Lesson extends LessonDraft {
  id: string;
  position: number;
  state: LessonState;
  topic_id: string | null;
  subject: string | null;
  step_vi: string;
  concepts: number;
  assessed: number;
  mastered: number;
  confirmed: boolean;
  material_goal: string | null;
}
export interface Curriculum {
  id: string;
  title: string;
  goal: string;
  completed: number;
  can_manage: boolean;
  lessons: Lesson[];
}
export interface CourseSummary {
  id: string;
  title: string;
  goal: string;
  lesson_count: number;
}
export interface ClassSummary {
  id: string;
  name: string;
  curriculum_id: string;
  curriculum_title: string;
  role: "teacher" | "student";
}
export interface Student {
  learner_id: string;
  name: string;
  completed: number;
  lessons: number;
  assessed_concepts: number;
  mean_mastery: number | null;
  attempts: number;
  correct_rate: number | null;
  last_active: string | null;
  lesson_states: LessonState[];
}
export interface WeakConcept {
  lesson: string;
  name: string;
  assessed: number;
  weak: number;
  unassessed: number;
  mean_mastery: number | null;
}
export interface Dashboard extends ClassSummary {
  invite_code: string;
  total_lessons: number;
  students: Student[];
  concepts: WeakConcept[];
}
export interface Material {
  graph: {
    concepts: { slug: string; name_vi: string; description_vi: string }[];
    edges: { from: string; to: string }[];
  };
  passages: {
    id: string;
    text: string;
    page: number | null;
    url: string;
    title: string;
    license: string;
  }[];
}

export class SchoolError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function schoolRequest<T>(
  path: string,
  options?: { body?: unknown; key?: string; signal?: AbortSignal },
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options?.body !== undefined) headers["Content-Type"] = "application/json";
  if (options?.key) headers["X-Class-Key"] = options.key;
  const response = await fetch(`/api/school/${path}`, {
    method: options?.body !== undefined ? "POST" : "GET",
    headers,
    body:
      options?.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
    signal: options?.signal,
  });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const message =
      data &&
      typeof data === "object" &&
      "detail" in data &&
      typeof data.detail === "string"
        ? data.detail
        : t.error;
    throw new SchoolError(response.status, message);
  }
  return response.json() as Promise<T>;
}

// Validate collections before rendering so a malformed backend response never looks like progress.
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error(t.error);
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== "string") throw new Error(t.error);
  return value;
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    throw new Error(t.error);
  return value;
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error(t.error);
  return value;
}
export function parseOutline(value: unknown): Outline {
  const o = object(value);
  const lessons = array(o.lessons).map((v) => {
    const l = object(v);
    return { module: text(l.module), title: text(l.title), goal: text(l.goal) };
  });
  if (lessons.length < 2 || lessons.length > 12) throw new Error(t.error);
  return { title: text(o.title), goal: text(o.goal), lessons };
}
export function parseCurriculum(value: unknown): Curriculum {
  const o = object(value);
  const outline = parseOutline(value);
  if (typeof o.can_manage !== "boolean") throw new Error(t.error);
  return {
    ...outline,
    id: text(o.id),
    completed: number(o.completed),
    can_manage: o.can_manage,
    lessons: array(o.lessons).map((v) => {
      const l = object(v);
      const state = text(l.state);
      if (!Object.hasOwn(t.states, state) || typeof l.confirmed !== "boolean")
        throw new Error(t.error);
      return {
        id: text(l.id),
        module: text(l.module),
        title: text(l.title),
        goal: text(l.goal),
        position: number(l.position),
        state: state as LessonState,
        topic_id: l.topic_id === null ? null : text(l.topic_id),
        subject: l.subject === null ? null : text(l.subject),
        step_vi: text(l.step_vi),
        concepts: number(l.concepts),
        assessed: number(l.assessed),
        mastered: number(l.mastered),
        confirmed: l.confirmed,
        material_goal: l.material_goal === null ? null : text(l.material_goal),
      };
    }),
  };
}
export function parseDashboard(value: unknown): Dashboard {
  const o = object(value);
  const nullable = (v: unknown) => {
    if (v === null) return null;
    const n = number(v);
    if (n > 1) throw new Error(t.error);
    return n;
  };
  if (o.role !== "teacher") throw new Error(t.error);
  return {
    id: text(o.id),
    name: text(o.name),
    curriculum_id: text(o.curriculum_id),
    curriculum_title: text(o.curriculum_title),
    role: "teacher",
    invite_code: text(o.invite_code),
    total_lessons: number(o.total_lessons),
    students: array(o.students).map((v) => {
      const s = object(v);
      const states = array(s.lesson_states).map((state) => {
        const key = text(state);
        if (!Object.hasOwn(t.states, key)) throw new Error(t.error);
        return key as LessonState;
      });
      return {
        learner_id: text(s.learner_id),
        name: text(s.name),
        completed: number(s.completed),
        lessons: number(s.lessons),
        assessed_concepts: number(s.assessed_concepts),
        mean_mastery: nullable(s.mean_mastery),
        attempts: number(s.attempts),
        correct_rate: nullable(s.correct_rate),
        last_active: s.last_active === null ? null : text(s.last_active),
        lesson_states: states,
      };
    }),
    concepts: array(o.concepts).map((v) => {
      const c = object(v);
      return {
        lesson: text(c.lesson),
        name: text(c.name),
        assessed: number(c.assessed),
        weak: number(c.weak),
        unassessed: number(c.unassessed),
        mean_mastery: nullable(c.mean_mastery),
      };
    }),
  };
}
export function errorMessage(error: unknown) {
  if (error instanceof DataError)
    return error.status === 503 ? t.contentUnavailable : t.error;
  return error instanceof Error && error.message ? error.message : t.error;
}

export interface LibraryLesson {
  topic_id: string;
  goal: string;
  concepts: string[];
}
export function parseLibrary(value: unknown): LibraryLesson[] {
  return array(value).map((v) => {
    const entry = object(v);
    return {
      topic_id: text(entry.topic_id),
      goal: text(entry.goal),
      concepts: array(entry.concepts).map(text),
    };
  });
}
export function percent(value: number | null) {
  return value === null ? t.notAssessed : `${Math.round(value * 100)}%`;
}

export function parseCourses(value: unknown): CourseSummary[] {
  return array(value).map((v) => {
    const c = object(v);
    return {
      id: text(c.id),
      title: text(c.title),
      goal: text(c.goal),
      lesson_count: number(c.lesson_count),
    };
  });
}
export function parseClasses(value: unknown): ClassSummary[] {
  return array(value).map((v) => {
    const c = object(v);
    if (c.role !== "teacher" && c.role !== "student") throw new Error(t.error);
    return {
      id: text(c.id),
      name: text(c.name),
      curriculum_id: text(c.curriculum_id),
      curriculum_title: text(c.curriculum_title),
      role: c.role,
    };
  });
}
export function parseSession(value: unknown): {
  learner_id: string;
  name: string;
} {
  const s = object(value);
  return { learner_id: text(s.learner_id), name: text(s.name) };
}
export function parseMaterial(value: unknown): Material {
  const m = object(value);
  const g = object(m.graph);
  return {
    graph: {
      concepts: array(g.concepts).map((v) => {
        const c = object(v);
        return {
          slug: text(c.slug),
          name_vi: text(c.name_vi),
          description_vi: text(c.description_vi),
        };
      }),
      edges: array(g.edges).map((v) => {
        const e = object(v);
        return { from: text(e.from), to: text(e.to) };
      }),
    },
    passages: array(m.passages).map((v) => {
      const p = object(v);
      return {
        id: text(p.id),
        text: text(p.text),
        page: p.page === null ? null : number(p.page),
        url: text(p.url),
        title: text(p.title),
        license: text(p.license),
      };
    }),
  };
}

export async function learnerRequest(
  path: string,
  body?: unknown,
): Promise<unknown> {
  const response = await fetch(`/api/backend/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    throw new SchoolError(
      response.status,
      data &&
        typeof data === "object" &&
        "detail" in data &&
        typeof data.detail === "string"
        ? data.detail
        : t.error,
    );
  }
  return response.json();
}
