export type StudyAction = "unlock" | "practice" | "backtrack";
export function studyAction(mastery: number, attempts: number): StudyAction {
  if (mastery >= 80) return "unlock";
  if (mastery < 50 && attempts >= 2) return "backtrack";
  return "practice";
}
export function examSchedule(days: number) {
  const count = Math.min(14, Math.max(3, Math.floor(days)));
  return Array.from({ length: count }, (_, i) => ({
    day: days - count + i,
    review: i >= count - 2,
    weak: i < count - 2 && i % 3 !== 0,
    concept: ["conditionals", "loops", "functions", "variables"][i % 4],
    minutes: 20,
  }));
}
export function mockCodePass(code: string): boolean {
  // Deliberately a fixture matcher, not a Python interpreter or a secure grader.
  return (
    /range\(\s*1\s*,\s*n\s*\+\s*1\s*\)/.test(code) &&
    /return\s+/.test(code) &&
    /total\s*\+=\s*i/.test(code)
  );
}
