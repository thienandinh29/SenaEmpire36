"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  errorMessage,
  parseLibrary,
  schoolRequest,
  type LibraryLesson,
} from "@/lib/school";
import { school as t } from "@/messages/school";

export function LibraryAssignment({
  course,
  lesson,
  refresh,
}: {
  course: string;
  lesson: string;
  refresh: () => Promise<void>;
}) {
  const [library, setLibrary] = useState<LibraryLesson[] | null>(null);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    if (library !== null || busy) return;
    setBusy(true);
    try {
      setLibrary(parseLibrary(await schoolRequest<unknown>("library")));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function assign() {
    if (busy || !selected) return;
    setBusy(true);
    setError("");
    try {
      await schoolRequest(`curricula/${course}/lessons/${lesson}/link`, {
        body: { topic_id: selected },
      });
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const material = library?.find((entry) => entry.topic_id === selected);
  return (
    <details
      className="school-library"
      onToggle={(e) => {
        if (e.currentTarget.open) void load();
      }}
    >
      <summary>{t.library}</summary>
      <p className="school-muted">{t.materialReview}</p>
      {error && (
        <p className="school-inline-error" role="alert">
          {error}
        </p>
      )}
      {library?.length ? (
        <>
          <label>
            {t.chooseMaterial}
            <select
              aria-label={t.chooseMaterial}
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="" disabled>
                {t.chooseMaterial}
              </option>
              {library.map((entry) => (
                <option key={entry.topic_id} value={entry.topic_id}>
                  {entry.goal}
                </option>
              ))}
            </select>
          </label>
          {material && (
            <ul>
              {material.concepts.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          )}
          <Button
            disabled={busy || !selected}
            variant="secondary"
            onClick={assign}
          >
            {busy ? t.loading : t.assign}
          </Button>
        </>
      ) : (
        <p>{busy || library === null ? t.loading : t.libraryEmpty}</p>
      )}
    </details>
  );
}
