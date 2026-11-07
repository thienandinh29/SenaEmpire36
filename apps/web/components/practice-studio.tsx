"use client";
import { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Check,
  Code2,
  Lightbulb,
  Play,
  RotateCcw,
} from "lucide-react";
import { studio as t } from "@/messages/studio";
import { mockCodePass, studyAction } from "@/lib/study-simulator";
import { Button } from "./ui/button";
import { Sena } from "./sena";
import type { Notebook } from "./study-tools";
export function PracticeStudio({ notebook }: { notebook: Notebook }) {
  const [tab, setTab] = useState(0);
  const [answer, setAnswer] = useState<number | null>(null);
  const [blank, setBlank] = useState("");
  const [blocks, setBlocks] = useState([2, 0, 3, 1]);
  const [code, setCode] = useState(
    "def total(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total",
  );
  const [result, setResult] = useState<boolean | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [mastery, setMastery] = useState(45);
  const [hint, setHint] = useState(false);
  const [hadError, setHadError] = useState(false);
  const action = studyAction(mastery, attempts);
  function submit() {
    if (result !== null) return;
    const pass =
      tab === 0
        ? answer === 1
        : tab === 1
          ? blank.trim() === "6"
          : tab === 2
            ? blocks.join() === "0,1,2,3"
            : mockCodePass(code);
    setResult(pass);
    setAttempts((v) => v + 1);
    setMastery((v) => (pass ? Math.min(98, v + 25) : Math.max(15, v - 10)));
    if (!pass) {
      setHadError(true);
      const card = {
        id: "diagnostic-range",
        question: t.cardQ,
        answer: t.cardA,
        concept: "loops",
      };
      notebook.persist(notebook.notes, [
        ...notebook.cards.filter((value) => value.id !== card.id),
        card,
      ]);
    }
  }
  function move(index: number, delta: number) {
    setBlocks((current) => {
      const next = [...current];
      [next[index], next[index + delta]] = [next[index + delta], next[index]];
      return next;
    });
    setResult(null);
  }
  return (
    <div className="studio-page">
      <div className="page-heading">
        <p className="eyebrow">{t.practice}</p>
        <h1>{t.labTitle}</h1>
        <p>{t.labBody}</p>
      </div>
      <div className="studio-grid">
        <section className="panel practice-panel">
          <div className="studio-tabs" role="group" aria-label={t.practice}>
            {t.formats.map((name, i) => (
              <button
                key={name}
                aria-pressed={tab === i}
                className={tab === i ? "active" : ""}
                onClick={() => {
                  setTab(i);
                  setResult(null);
                }}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="practice-content">
            <span className="pill">
              <Code2 size={14} />
              {t.labBody}
            </span>
            <h2>
              {tab === 0
                ? t.question
                : tab === 1
                  ? t.blank
                  : tab === 2
                    ? t.order
                    : t.codeTask}
            </h2>
            {tab === 0 && (
              <>
                <pre className="code-window">
                  <span>Python 3</span>
                  <code>{t.code}</code>
                </pre>
                <fieldset className="studio-options">
                  <legend className="sr-only">{t.question}</legend>
                  {t.options.map((option, i) => (
                    <label
                      key={option}
                      className={answer === i ? "selected" : ""}
                    >
                      <input
                        type="radio"
                        name="studio-answer"
                        checked={answer === i}
                        onChange={() => {
                          setAnswer(i);
                          setResult(null);
                        }}
                      />
                      <b>{String.fromCharCode(65 + i)}</b>
                      {option}
                    </label>
                  ))}
                </fieldset>
              </>
            )}
            {tab === 1 && (
              <>
                <pre className="code-window">
                  <code>{"for i in range(1, ___):\n    print(i)"}</code>
                </pre>
                <label className="field-label" htmlFor="blank-answer">
                  {t.blankLabel}
                </label>
                <input
                  id="blank-answer"
                  className="studio-input"
                  inputMode="numeric"
                  value={blank}
                  onChange={(e) => {
                    setBlank(e.target.value);
                    setResult(null);
                  }}
                />
              </>
            )}
            {tab === 2 && (
              <div className="code-blocks">
                {blocks.map((block, i) => (
                  <div key={block}>
                    <span>{i + 1}</span>
                    <code>{t.blocks[block]}</code>
                    <button
                      disabled={i === 0}
                      aria-label={`${t.up}: ${t.blocks[block]}`}
                      onClick={() => move(i, -1)}
                    >
                      <ArrowUp size={16} />
                    </button>
                    <button
                      disabled={i === 3}
                      aria-label={`${t.down}: ${t.blocks[block]}`}
                      onClick={() => move(i, 1)}
                    >
                      <ArrowDown size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {tab === 3 && (
              <>
                <label className="field-label" htmlFor="python-editor">
                  {t.editor}
                </label>
                <textarea
                  id="python-editor"
                  className="code-editor"
                  spellCheck={false}
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setResult(null);
                  }}
                />
                <p className="fine-print">{t.codeMock}</p>
              </>
            )}
            <div className="question-actions">
              <Button
                disabled={
                  result !== null ||
                  (tab === 0
                    ? answer === null
                    : tab === 1
                      ? !blank.trim()
                      : false)
                }
                onClick={submit}
              >
                {tab === 3 ? <Play size={16} /> : <Check size={16} />}{" "}
                {tab === 3 ? t.run : t.check}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setResult(null);
                  setAnswer(null);
                  setBlank("");
                }}
              >
                <RotateCcw size={15} />
                {t.retry}
              </Button>
            </div>
            <div aria-live="polite">
              {result !== null && (
                <div className={`feedback ${result ? "correct" : "incorrect"}`}>
                  <strong>{result ? t.correct : t.incorrect}</strong>
                  <p>
                    {result
                      ? tab === 0
                        ? t.correctBody
                        : t.states[2]
                      : tab === 2
                        ? t.orderError
                        : tab === 3
                          ? t.codeError
                          : tab === 1
                            ? t.blankError
                            : t.distractors[answer ?? 0]}
                  </p>
                  {tab === 3 && (
                    <div className="test-results">
                      {[0, 1, 5, 10].map((n, i) => (
                        <span key={n}>
                          {result || i < 2 ? "✓" : "×"} total({n}) →{" "}
                          {[0, 1, 15, 55][i]}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="mastery-row">
              <span>{t.mastery}</span>
              <strong>{mastery}%</strong>
            </div>
            <div className="progress-track">
              <span style={{ width: `${mastery}%` }} />
            </div>
            <div className="rule-result">
              <p className="eyebrow">{t.route}</p>
              <p>
                {action === "unlock"
                  ? t.routeGood
                  : action === "backtrack"
                    ? t.routeBack
                    : t.routePractice}
              </p>
              {action === "backtrack" && (
                <div className="route-chips">
                  {t.routeSteps.map((step, i) => (
                    <span
                      key={step}
                      className={i === 1 || i === 2 ? "inserted" : ""}
                    >
                      {step}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
        <aside className="panel studio-tutor">
          <Sena
            size={170}
            mood={result === null ? "focus" : result ? "happy" : "oops"}
          />
          <span className="pill">
            {t.states[result === null ? 1 : result ? 2 : 3]}
          </span>
          <h2>{t.hint}</h2>
          <p>{t.hintBody}</p>
          {hint && (
            <div className="hint-bubble">
              <Lightbulb size={18} />
              <p>{hadError ? t.hintPast : t.hintBody}</p>
              <p>{t.hintNote}</p>
              {notebook.notes.loops && (
                <blockquote>{notebook.notes.loops}</blockquote>
              )}
              <a href={t.sourceUrl} target="_blank" rel="noreferrer">
                {t.source}
              </a>
            </div>
          )}
          <Button variant="secondary" onClick={() => setHint((v) => !v)}>
            <Lightbulb size={16} />
            {t.hintAction}
          </Button>
          <small>{t.mock}</small>
        </aside>
      </div>
    </div>
  );
}
export function PlacementStudio() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [scores, setScores] = useState<Record<number, number>>({});
  const [chosen, setChosen] = useState<number | null>(null);
  const [remaining, setRemaining] = useState(600);
  const [done, setDone] = useState(false);
  const [feedback, setFeedback] = useState("");
  const running = started && !done && remaining > 0;
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(
      () => setRemaining((value) => Math.max(0, value - 1)),
      1000,
    );
    return () => clearInterval(timer);
  }, [running]);
  const finished = done || (started && remaining === 0);
  function submit() {
    if (chosen === null) return;
    const correct = chosen === 1;
    setScores((v) => ({ ...v, [step]: correct ? 85 : 35 }));
    setFeedback(t.placementAdapt[correct ? 0 : 1]);
    setChosen(null);

    if (step === 2) setDone(true);
    else setStep(correct ? Math.min(2, step + 1) : 2);
  }
  function skillScore(index: number): number | undefined {
    return scores[({ 1: 2, 2: 1, 3: 0 } as Record<number, number>)[index]];
  }
  const weakest = [1, 2, 3]
    .filter((index) => skillScore(index) !== undefined)
    .sort((a, b) => (skillScore(a) ?? 100) - (skillScore(b) ?? 100))[0];
  return (
    <section className="panel placement-panel">
      <Sena size={140} mood={finished ? "think" : "hello"} />
      <p className="eyebrow">{t.placement}</p>
      <h1>{finished ? t.placementResult : t.placement}</h1>
      <p>{t.placementBody}</p>
      {!started ? (
        <Button onClick={() => setStarted(true)}>{t.placementStart}</Button>
      ) : finished ? (
        <>
          <div className="skill-bars">
            {t.placementSkills.map((skill, i) => (
              <div key={skill}>
                <span>{skill}</span>
                <strong>
                  {skillScore(i) === undefined
                    ? t.pending
                    : `${skillScore(i)}%`}
                </strong>
                <div className="progress-track">
                  <span
                    style={{
                      width: `${skillScore(i) ?? 0}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="diagnosis">
            {Object.values(scores).some((score) => score < 50)
              ? `${t.rootPrefix} ${t.placementSkills[weakest]}`
              : t.correct}
          </p>
          <Button
            variant="secondary"
            onClick={() => {
              setStarted(false);
              setDone(false);
              setStep(0);
              setScores({});
              setRemaining(600);
              setFeedback("");
            }}
          >
            {t.reset}
          </Button>
        </>
      ) : (
        <>
          <span className="pill">
            {Math.floor(remaining / 60)}:
            {String(remaining % 60).padStart(2, "0")} · {t.mock}
          </span>
          <h2>{t.placementQuestions[step]}</h2>
          <div className="studio-options">
            {t.placementOptions[step].map((option, i) => (
              <button
                key={option}
                aria-pressed={chosen === i}
                className={chosen === i ? "selected" : ""}
                onClick={() => setChosen(i)}
              >
                {option}
              </button>
            ))}
          </div>
          <Button disabled={chosen === null} onClick={submit}>
            {t.check}
          </Button>
          <p role="status">{feedback}</p>
        </>
      )}
    </section>
  );
}
