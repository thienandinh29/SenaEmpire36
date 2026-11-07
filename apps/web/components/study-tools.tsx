"use client";
import { useEffect, useState } from "react";
import {
  CalendarDays,
  Check,
  ChevronRight,
  FileText,
  FlipHorizontal,
  Plus,
  Save,
} from "lucide-react";
import { studio as t } from "@/messages/studio";
import type { KnowledgeGraph } from "@/lib/contracts";
import { examSchedule } from "@/lib/study-simulator";
import { Button } from "./ui/button";
import { Sena } from "./sena";
export interface Flashcard {
  id: string;
  question: string;
  answer: string;
  concept: string;
  due?: string;
}
const sample: Flashcard = {
  id: "sample-range",
  question: t.cardQ,
  answer: t.cardA,
  concept: "loops",
};
export function useStudyNotebook() {
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [cards, setCards] = useState<Flashcard[]>([sample]);
  const [storageReady, setStorageReady] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        const raw = localStorage.getItem("nodetrail-notebook-v1");
        if (raw) {
          const data: unknown = JSON.parse(raw);
          if (
            typeof data === "object" &&
            data !== null &&
            "notes" in data &&
            "cards" in data
          ) {
            const n = data.notes;
            const c = data.cards;
            if (
              typeof n === "object" &&
              n !== null &&
              !Array.isArray(n) &&
              Object.values(n).every((v) => typeof v === "string")
            )
              setNotes(n as Record<string, string>);
            if (Array.isArray(c))
              setCards(
                c.filter(
                  (v): v is Flashcard =>
                    typeof v === "object" &&
                    v !== null &&
                    typeof v.id === "string" &&
                    typeof v.question === "string" &&
                    typeof v.answer === "string" &&
                    typeof v.concept === "string",
                ),
              );
          }
        }
      } catch {}
      setStorageReady(true);
    }, 0);
    return () => clearTimeout(timer);
  }, []);
  function persist(nextNotes: Record<string, string>, nextCards: Flashcard[]) {
    setNotes(nextNotes);
    setCards(nextCards);
    try {
      localStorage.setItem(
        "nodetrail-notebook-v1",
        JSON.stringify({ notes: nextNotes, cards: nextCards }),
      );
      return true;
    } catch {
      return false;
    }
  }
  return { notes, cards, storageReady, persist };
}
export type Notebook = ReturnType<typeof useStudyNotebook>;
export function NoteStudio({
  graph,
  selected,
  notebook,
}: {
  graph: KnowledgeGraph;
  selected: string;
  notebook: Notebook;
}) {
  const [node, setNode] = useState(selected || graph.nodes[0]?.slug || "loops");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const text = drafts[node] ?? notebook.notes[node] ?? "";
  const title = graph.nodes.find((n) => n.slug === node)?.name_vi || node;
  function update(value: string) {
    setDrafts((v) => ({ ...v, [node]: value }));
    setStatus("");
  }
  function save() {
    if (!text.trim()) {
      setStatus(t.emptyNote);
      return;
    }
    const card: Flashcard = {
      id: `note-${node}`,
      question: `${t.noteQ} ${title}?`,
      answer: text,
      concept: node,
    };
    const cards = [...notebook.cards.filter((c) => c.id !== card.id), card];
    setStatus(
      notebook.persist({ ...notebook.notes, [node]: text }, cards)
        ? t.saved
        : t.storageError,
    );
  }
  return (
    <div className="studio-page">
      <div className="page-heading">
        <p className="eyebrow">{t.notes}</p>
        <h1>{t.notes}</h1>
        <p>{t.noteBody}</p>
      </div>
      <div className="notebook-grid">
        <aside className="panel notebook-index">
          <p className="eyebrow">{t.node}</p>
          {graph.nodes.map((n) => (
            <button
              key={n.slug}
              className={node === n.slug ? "active" : ""}
              onClick={() => {
                setNode(n.slug);
                setStatus("");
              }}
            >
              <FileText size={16} />
              <span>{n.name_vi}</span>
              {notebook.notes[n.slug] && <Check size={14} />}
            </button>
          ))}
        </aside>
        <section className="panel note-editor">
          <div className="note-toolbar">
            <span className="pill">
              <FileText size={14} />
              {title}
            </span>
            <span>{t.mock}</span>
          </div>
          <h2>{title}</h2>
          <label className="field-label" htmlFor="note-text">
            {t.noteLabel}
          </label>
          <textarea
            id="note-text"
            value={text}
            placeholder={t.notePlaceholder}
            onChange={(e) => update(e.target.value)}
          />
          <p className="fine-print">{t.slash}</p>
          <div className="block-toolbar">
            {t.blockTypes.map((type, i) => (
              <button
                key={type}
                onClick={() =>
                  update(text.replace(/\/$/, "") + t.blockValues[i])
                }
              >
                <Plus size={13} />
                {type}
              </button>
            ))}
          </div>
          <div className="note-actions">
            <Button disabled={!notebook.storageReady} onClick={save}>
              <Save size={16} />
              {t.save}
            </Button>
            <span role="status">{status}</span>
          </div>
          {text && (
            <div className="note-preview">
              <p className="eyebrow">{t.back}</p>
              <pre>{text}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
export function FlashcardStudio({ notebook }: { notebook: Notebook }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [message, setMessage] = useState("");
  const [sessionTime] = useState(() => Date.now());
  const dueCards = notebook.cards.filter(
    (card) => !card.due || new Date(card.due).getTime() <= sessionTime,
  );
  const card = dueCards[0];
  function rate(rating: number) {
    if (!card) return;
    const days = [10 / 1440, 1, 3, 7][rating];
    const next = notebook.cards.map((c) =>
      c.id === card.id
        ? { ...c, due: new Date(Date.now() + days * 86400000).toISOString() }
        : c,
    );
    notebook.persist(notebook.notes, next);
    setMessage(`${t.scheduled} ${t.intervals[rating]}.`);
    setIndex((v) => v + 1);
    setFlipped(false);
  }
  return (
    <section className="flashcard-section">
      <div className="page-heading">
        <p className="eyebrow">{t.flashcards}</p>
        <h1>{t.flashcards}</h1>
        <p>{t.flashBody}</p>
      </div>
      <div className="panel flashcard-panel">
        {card ? (
          <>
            <div className="note-toolbar">
              <span className="pill">{graphLabel(card.concept)}</span>
              <span>
                {index + 1} / {index + dueCards.length}
              </span>
            </div>
            <button
              className={`flashcard ${flipped ? "flipped" : ""}`}
              onClick={() => setFlipped((v) => !v)}
              aria-label={t.flip}
            >
              <span className="eyebrow">{flipped ? t.back : t.front}</span>
              <strong>{flipped ? card.answer : card.question}</strong>
              <span>
                <FlipHorizontal size={16} />
                {t.flip}
              </span>
            </button>
            {flipped ? (
              <div className="rating-buttons">
                {t.ratings.map((label, i) => (
                  <button key={label} onClick={() => rate(i)}>
                    <strong>{label}</strong>
                    <small>{t.intervals[i]}</small>
                  </button>
                ))}
              </div>
            ) : (
              <Button variant="secondary" onClick={() => setFlipped(true)}>
                {t.flip}
              </Button>
            )}
          </>
        ) : (
          <div className="flashcard-complete">
            <Sena size={180} mood="happy" />
            <h2>{t.complete}</h2>
            <Button
              onClick={() => {
                notebook.persist(
                  notebook.notes,
                  notebook.cards.map((card) => ({ ...card, due: undefined })),
                );
                setIndex(0);
                setFlipped(false);
              }}
            >
              {t.again}
            </Button>
          </div>
        )}
        <p role="status">{message}</p>
      </div>
    </section>
  );
}
function graphLabel(slug: string) {
  return slug === "loops" ? `Python · ${t.loops}` : slug;
}
export function ExamCalendar() {
  const [date, setDate] = useState("");
  const [selected, setSelected] = useState(0);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const delta = date
    ? Math.round(
        (new Date(`${date}T00:00:00`).getTime() - now.getTime()) / 86400000,
      )
    : 14;
  const valid = Number.isFinite(delta) && delta >= 3 && delta <= 90;
  const plan = examSchedule(valid ? delta : 14);
  return (
    <div className="studio-page">
      <div className="page-heading">
        <p className="eyebrow">{t.calendar}</p>
        <h1>{t.calendarTitle}</h1>
        <p>{t.calendarBody}</p>
      </div>
      <div className="panel calendar-settings">
        <span className="detail-icon">
          <CalendarDays size={24} />
        </span>
        <div>
          <label className="field-label" htmlFor="exam-date">
            {t.examDate}
          </label>
          <input
            id="exam-date"
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setSelected(0);
            }}
          />
          {!valid && (
            <p className="error-text" role="alert">
              {t.dateError}
            </p>
          )}
        </div>
        <div className="countdown-number">
          <strong>{valid ? delta : "—"}</strong>
          <span>{t.days}</span>
        </div>
        <span className="pill">20 {t.minutes}</span>
      </div>
      <div className="calendar-legend">
        <span className="pill weak">{t.weak}</span>
        <span className="pill">{t.stable}</span>
        <span className="pill review">{t.overview}</span>
      </div>
      <div className="exam-grid">
        {plan.map((day, i) => (
          <button
            key={day.day}
            aria-pressed={selected === i}
            className={`exam-day ${day.review ? "review" : day.weak ? "weak" : ""} ${selected === i ? "active" : ""}`}
            onClick={() => setSelected(i)}
          >
            <span>
              {t.day} {i + 1}
            </span>
            <strong>
              {day.review
                ? t.overview
                : day.concept === "loops"
                  ? t.loops
                  : day.concept === "conditionals"
                    ? t.conditionals
                    : day.concept === "functions"
                      ? t.functions
                      : t.variables}
            </strong>
            <small>
              <CalendarDays size={13} />
              20 {t.minutes.split(" /")[0]}
            </small>
            {day.review ? <Check size={18} /> : <ChevronRight size={18} />}
          </button>
        ))}
      </div>
      <section className="panel day-detail">
        <Sena size={110} mood="think" />
        <div>
          <p className="eyebrow">
            {t.day} {selected + 1}
          </p>
          <h2>{plan[selected]?.review ? t.overview : t.weak}</h2>
          <p>{plan[selected]?.review ? t.calendarBody : t.routePractice}</p>
          <p className="fine-print">{t.scheduleNote}</p>
        </div>
      </section>
    </div>
  );
}
