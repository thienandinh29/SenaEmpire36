"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import { vi as t } from "@/messages/vi";
import { THEME_STORAGE_KEY } from "@/lib/theme";

type Theme = "light" | "dark";
const changeEvent = "nodetrail-theme-change";

function applyTheme(theme: Theme, preference: "user" | "system") {
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.themePreference = preference;
  document.documentElement.style.colorScheme = theme;
  window.dispatchEvent(new Event(changeEvent));
}

function subscribe(onChange: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  function followSystem() {
    if (document.documentElement.dataset.themePreference !== "user")
      applyTheme(media.matches ? "dark" : "light", "system");
  }
  function syncStorage(event: StorageEvent) {
    if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
    const value = event.newValue;
    const explicit = value === "dark" || value === "light";
    applyTheme(
      explicit ? value : media.matches ? "dark" : "light",
      explicit ? "user" : "system",
    );
  }
  window.addEventListener(changeEvent, onChange);
  window.addEventListener("storage", syncStorage);
  media.addEventListener("change", followSystem);
  return () => {
    window.removeEventListener(changeEvent, onChange);
    window.removeEventListener("storage", syncStorage);
    media.removeEventListener("change", followSystem);
  };
}

const getSnapshot = () => document.documentElement.dataset.theme === "dark";
const getServerSnapshot = () => false;

export function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const label = dark ? t.theme.switchToLight : t.theme.switchToDark;
  function toggle() {
    const next = dark ? "light" : "dark";
    applyTheme(next, "user");
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // The selected theme still works for this page when storage is blocked.
    }
  }
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={label}
      title={label}
      aria-pressed={dark}
    >
      <Sun className="theme-sun" size={18} aria-hidden="true" />
      <Moon className="theme-moon" size={18} aria-hidden="true" />
    </button>
  );
}
