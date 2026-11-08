"use client";

import type { GraphReview, ReviewedConcept } from "@/lib/decode";
import { vi as t } from "@/messages/vi";
import { SourceLink } from "./source-link";

export function AssessmentReview({
  assessment,
  concepts,
}: {
  assessment: GraphReview["assessment"];
  concepts: ReviewedConcept[];
}) {
  if (!assessment) return null;
  return (
    <section aria-label={t.live.assessmentTitle}>
      <p>
        {t.live.answered}: {assessment.answered} · {t.live.correctCount}:{" "}
        {assessment.correct} · {t.live.incorrectCount}: {assessment.incorrect}
      </p>
      {assessment.concepts.map((entry) => {
        const concept = concepts.find((c) => c.slug === entry.slug);
        return (
          <article key={entry.slug} className="panel">
            <h3>{concept?.name_vi || entry.slug}</h3>
            <strong>{t.live[entry.priority]}</strong>
            {entry.important && <p>{t.live.important}</p>}
            <p>
              {t.live.correctCount}: {entry.correct} · {t.live.incorrectCount}:{" "}
              {entry.incorrect}
            </p>
            {entry.mistakes.map((mistake, index) => (
              <div key={index}>
                <p>{mistake.question}</p>
                <p>
                  {t.live.chosenAnswer}: {mistake.chosen_answer}
                </p>
                {mistake.misconception_vi && (
                  <p>
                    {t.live.misconceptionNote}: {mistake.misconception_vi}
                  </p>
                )}
              </div>
            ))}
            <h4>{t.live.reviewContent}</h4>
            <p>{concept?.description_vi}</p>
            {concept?.sources.map((url) => (
              <SourceLink key={url} url={url} title={t.sources} />
            ))}
          </article>
        );
      })}
    </section>
  );
}
