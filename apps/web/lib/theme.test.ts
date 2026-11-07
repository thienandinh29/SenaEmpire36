import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";
import { THEME_STORAGE_KEY, themeBootstrap } from "./theme";

function boot(saved: string | null, systemDark: boolean, blocked = false) {
  const root = {
    dataset: {} as Record<string, string>,
    style: { colorScheme: "" },
  };
  runInNewContext(themeBootstrap, {
    document: { documentElement: root },
    localStorage: {
      getItem: (key: string) => {
        expect(key).toBe(THEME_STORAGE_KEY);
        if (blocked) throw new Error("Storage blocked");
        return saved;
      },
    },
    window: { matchMedia: () => ({ matches: systemDark }) },
  });
  return root;
}

describe("theme before first paint", () => {
  it("restores an explicit light choice over a dark system preference", () => {
    const root = boot("light", true);
    expect(root.dataset).toEqual({ theme: "light", themePreference: "user" });
    expect(root.style.colorScheme).toBe("light");
  });
  it("restores dark mode on reload even when the OS uses light mode", () => {
    expect(boot("dark", false).dataset.theme).toBe("dark");
  });
  it("follows the OS until a valid preference has been saved", () => {
    expect(boot(null, true).dataset).toEqual({
      theme: "dark",
      themePreference: "system",
    });
    expect(boot("invalid", false).dataset.theme).toBe("light");
  });
  it("still initializes when the browser blocks localStorage", () => {
    expect(boot(null, true, true).style.colorScheme).toBe("dark");
  });
});
