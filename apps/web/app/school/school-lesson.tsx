"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, BookOpen, CheckCircle2, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceLink } from "@/components/source-link";
import { createLearningClient } from "@/lib/data-client";
import { parseItem, record, string } from "@/lib/decode";
import type { AttemptResult, HintResult, PublicItem } from "@/lib/contracts";
import type { WebConfig } from "@/lib/config";
import {
  errorMessage,
  learnerRequest,
  parseMaterial,
  schoolRequest,
  type Lesson,
  type Material,
} from "@/lib/school";
import { school as t } from "@/messages/school";

export function SchoolLesson({
  course,
  lesson,
  learner,
  config,
  back,
  progress,
}: {
  course: string;
  lesson: Lesson;
  learner: string;
  config: WebConfig;
  back: () => void;
  progress: () => Promise<boolean>;
}) {
  const client = useMemo(() => createLearningClient(config), [config]);
  const [material, setMaterial] = useState<Material | null>(null);
  const [revision, setRevision] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [placementDone, setPlacementDone] = useState(false);
  const [item, setItem] = useState<PublicItem | null>(null);
  const [answer, setAnswer] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<AttemptResult | null>(null);
  const [hints, setHints] = useState<HintResult[]>([]);
  const [complete, setComplete] = useState(lesson.state === "completed");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const subject = lesson.subject ?? "";
  useEffect(() => {
    let active = true;
    Promise.all([
      schoolRequest<unknown>(
        `curricula/${course}/lessons/${lesson.id}/material`,
      ).then(parseMaterial),
      learnerRequest(`graph/review?${new URLSearchParams({ subject })}`),
    ])
      .then(([m, value]) => {
        if (!active) return;
        const review = record(value);
        setMaterial(m);
        setRevision(string(review.graph_revision));
        setConfirmed(review.confirmed === true);
      })
      .catch((e) => {
        if (active) setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [course, lesson.id, subject]);

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
  async function next() {
    if (await progress()) {
      setComplete(true);
      return;
    }
    let nextItem: PublicItem | null = null;
    if (!placementDone) {
      const placement = await client.placement(learner, subject, "");
      nextItem = placement.item;
      if (placement.done) {
        setPlacementDone(true);
        const value = record(
          await learnerRequest(
            `next-item?${new URLSearchParams({ learner_id: learner, subject })}`,
          ),
        );
        nextItem = parseItem(value.item);
      }
    } else {
      const value = record(
        await learnerRequest(
          `next-item?${new URLSearchParams({ learner_id: learner, subject })}`,
        ),
      );
      nextItem = parseItem(value.item);
    }
    setItem(nextItem);
    setAnswer(null);
    setFeedback(null);
    setHints([]);
  }
  return (
    <section className="school-lesson">
      <Button variant="ghost" onClick={back}>
        <ArrowLeft size={16} aria-hidden="true" />
        {t.quit}
      </Button>
      <div className="school-section-heading">
        <div>
          <span className="school-eyebrow">
            {lesson.module} · {t.lesson} {lesson.position}
          </span>
          <h1>{lesson.title}</h1>
          <p>{lesson.goal}</p>
        </div>
        <BookOpen size={30} aria-hidden="true" />
      </div>
      {error && (
        <p className="school-error" role="alert">
          {error}
        </p>
      )}
      {!material && !error && <p role="status">{t.loading}</p>}
      {material && (
        <div className="school-reading-grid">
          <section className="school-panel">
            <h2>{t.original}</h2>
            <p className="school-muted">{t.originalHint}</p>
            {material.passages.map((p, index) => (
              <details key={p.id} open={index === 0}>
                <summary>
                  {p.title}
                  {p.page ? ` · ${t.page} ${p.page}` : ""}
                </summary>
                <p className="school-source-text">{p.text}</p>
                <div className="school-source-footer">
                  <SourceLink
                    url={p.url}
                    title={p.title}
                    page={p.page ?? undefined}
                  />
                  <small>{p.license}</small>
                </div>
              </details>
            ))}
          </section>
          <section className="school-panel school-practice">
            <span className="school-eyebrow">
              {placementDone ? t.practice : t.placement}
            </span>
            {!confirmed ? (
              <>
                <h2>{t.confirmation}</h2>
                <ul className="school-concepts">
                  {material.graph.concepts.map((c) => (
                    <li key={c.slug}>
                      <strong>{c.name_vi}</strong>
                      <p>{c.description_vi}</p>
                    </li>
                  ))}
                </ul>
                <h3>{t.prerequisites}</h3>
                {material.graph.edges.length ? (
                  <ul className="school-concepts">
                    {material.graph.edges.map((edge) => (
                      <li key={`${edge.from}-${edge.to}`}>
                        {
                          material.graph.concepts.find(
                            (concept) => concept.slug === edge.from,
                          )?.name_vi
                        }{" "}
                        {t.before}{" "}
                        {
                          material.graph.concepts.find(
                            (concept) => concept.slug === edge.to,
                          )?.name_vi
                        }
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="school-muted">{t.noPrerequisites}</p>
                )}
                <Button
                  disabled={!revision || busy}
                  onClick={() =>
                    run(async () => {
                      await learnerRequest("graph/confirm", {
                        subject,
                        graph_revision: revision,
                      });
                      setConfirmed(true);
                    })
                  }
                >
                  {t.confirm}
                </Button>
              </>
            ) : complete ? (
              <div className="school-complete">
                <CheckCircle2 size={38} aria-hidden="true" />
                <h2>{t.done}</h2>
                <p>{t.completeHint}</p>
                <Button onClick={back}>{t.quit}</Button>
              </div>
            ) : !item ? (
              <>
                <h2>{t.understand}</h2>
                <Button disabled={busy} onClick={() => run(next)}>
                  {busy ? t.loading : t.start}
                </Button>
              </>
            ) : (
              <>
                <h2>{item.prompt_vi}</h2>
                <fieldset
                  className="school-options"
                  disabled={busy || feedback !== null}
                >
                  <legend className="school-sr-only">{t.submit}</legend>
                  {item.options.map((option, index) => (
                    <label key={`${item.id}-${index}`}>
                      <input
                        type="radio"
                        name="school-answer"
                        value={index}
                        checked={answer === index}
                        onChange={() => setAnswer(index)}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </fieldset>
                {!feedback ? (
                  <div className="school-actions">
                    <Button
                      disabled={answer === null || busy}
                      onClick={() =>
                        run(async () => {
                          if (answer === null) return;
                          const value = await client.attempt(
                            learner,
                            item,
                            "",
                            answer,
                            hints.length,
                          );
                          setFeedback(value);
                          if (await progress()) setComplete(true);
                        })
                      }
                    >
                      {busy ? t.loading : t.submit}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy || hints.length >= 3}
                      onClick={() =>
                        run(async () => {
                          setHints([
                            ...hints,
                            await client.hint(
                              learner,
                              item,
                              "",
                              hints.length,
                              "pro",
                            ),
                          ]);
                        })
                      }
                    >
                      <Lightbulb size={16} aria-hidden="true" />
                      {hints.length >= 3 ? t.hintLimit : t.hint}
                    </Button>
                  </div>
                ) : (
                  <div className="school-feedback" role="status">
                    <strong>
                      {feedback.correct ? t.correct : t.incorrect}
                    </strong>
                    {feedback.misconception_vi && (
                      <p>{feedback.misconception_vi}</p>
                    )}
                    {feedback.remediation && (
                      <p>{feedback.remediation.reason_vi}</p>
                    )}
                    <Button disabled={busy} onClick={() => run(next)}>
                      {t.next}
                    </Button>
                  </div>
                )}
                {hints.map((hint, index) => (
                  <div className="school-hint" key={index}>
                    <strong>
                      {t.hint} {index + 1}
                    </strong>
                    <p>{hint.hint_vi}</p>
                    {hint.citations.map((c) => (
                      <SourceLink key={c.url} url={c.url} title={c.title} />
                    ))}
                  </div>
                ))}
              </>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
