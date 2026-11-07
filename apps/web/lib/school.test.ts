import { describe, expect, it } from "vitest";
import {
  parseCurriculum,
  parseDashboard,
  parseOutline,
  percent,
} from "./school";
import { school as t } from "@/messages/school";

const outline = {
  title: "Python",
  goal: "Learn Python foundations",
  lessons: [
    {
      module: "Foundations",
      title: "Conditions",
      goal: "Python if statements",
    },
    { module: "Application", title: "Loops", goal: "Python for loops" },
  ],
};
describe("school data boundaries", () => {
  it("keeps AI outlines as plans without invented readiness", () => {
    expect(parseOutline(outline)).toEqual(outline);
    expect(() => parseOutline({ ...outline, lessons: [] })).toThrow();
  });
  it.each(["ready-now", "toString", "constructor"])(
    "rejects invalid lesson state %s",
    (state) => {
      expect(() =>
        parseCurriculum({
          ...outline,
          id: "course",
          completed: 0,
          can_manage: true,
          lessons: outline.lessons.map((l) => ({
            ...l,
            state,
            id: "lesson",
            position: 1,
            topic_id: null,
            subject: null,
            step_vi: "",
            concepts: 0,
            assessed: 0,
            mastered: 0,
            confirmed: false,
            material_goal: null,
          })),
        }),
      ).toThrow();
    },
  );
  it("distinguishes unknown mastery from measured zero", () => {
    expect(percent(null)).toBe(t.notAssessed);
    expect(percent(0)).toBe("0%");
    const dashboard = {
      id: "class",
      name: "Class",
      curriculum_id: "course",
      curriculum_title: "Python",
      role: "teacher",
      invite_code: "invite",
      total_lessons: 2,
      students: [
        {
          learner_id: "learner",
          name: "New student",
          completed: 0,
          lessons: 2,
          assessed_concepts: 0,
          mean_mastery: null,
          attempts: 0,
          correct_rate: null,
          last_active: null,
          lesson_states: ["not_started", "locked"],
        },
      ],
      concepts: [],
    };
    expect(parseDashboard(dashboard).students[0].mean_mastery).toBeNull();
    expect(() => parseDashboard({ ...dashboard, role: "student" })).toThrow();
    expect(() =>
      parseDashboard({
        ...dashboard,
        students: [{ ...dashboard.students[0], mean_mastery: 2 }],
      }),
    ).toThrow();
  });
});
