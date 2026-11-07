import { describe, expect, it } from "vitest";
import { examSchedule, studyAction, mockCodePass } from "./study-simulator";
describe("mock learning rules", () => {
  it("unlocks at 80 and retains learners at 50", () => {
    expect(studyAction(80, 1)).toBe("unlock");
    expect(studyAction(50, 2)).toBe("practice");
  });
  it("requires two attempts before backtracking", () => {
    expect(studyAction(35, 1)).toBe("practice");
    expect(studyAction(35, 2)).toBe("backtrack");
  });
  it("reserves the two days before the exam for review", () => {
    const plan = examSchedule(14);
    expect(plan).toHaveLength(14);
    expect(plan.slice(-2).map((day) => day.day)).toEqual([12, 13]);
    expect(plan.filter((day) => day.review)).toHaveLength(2);
    expect(plan.every((day) => day.minutes === 20)).toBe(true);
  });
  it("bounds distant exams to the last 14 study days", () => {
    const plan = examSchedule(90);
    expect(plan[0].day).toBe(76);
    expect(plan.at(-1)?.day).toBe(89);
  });
  it("does not pass the intentionally incorrect code fixture", () => {
    expect(mockCodePass("for i in range(1, n): total += i; return total")).toBe(
      false,
    );
    expect(
      mockCodePass("for i in range(1, n + 1): total += i; return total"),
    ).toBe(true);
  });
});
