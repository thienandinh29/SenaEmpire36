"use client";

import {
  ArrowRight,
  BookOpen,
  ChevronUp,
  Code2,
  Compass,
  NotebookPen,
  Plus,
  RotateCcw,
  CalendarDays,
} from "lucide-react";
import { journal as j } from "@/messages/journal";
import { vi as t } from "@/messages/vi";
import type { KnowledgeGraph } from "@/lib/contracts";
import { KnowledgeMap } from "./knowledge-map";
import { Sena } from "./sena";
import { Button } from "./ui/button";
import { ErrorState, Loading } from "./async-state";

type Destination =
  "map" | "learn" | "reviews" | "notes" | "practice" | "calendar";
interface Props {
  graph: KnowledgeGraph;
  selected: string;
  subject: string;
  approved: boolean;
  mock: boolean;
  notes: Record<string, string>;
  cardCount: number;
  loading?: boolean;
  error?: unknown;
  onSelect: (slug: string) => void;
  onRetry: () => void;
  onNavigate: (destination: Destination) => void;
  onNewTopic: () => void;
  onWhy: () => void;
}

export function JournalOverview({
  graph,
  selected,
  subject,
  approved,
  mock,
  notes,
  cardCount,
  loading,
  error,
  onSelect,
  onRetry,
  onNavigate,
  onNewTopic,
  onWhy,
}: Props) {
  const current = graph.nodes.find((node) => node.slug === selected);
  const mastered = graph.nodes.filter((node) => node.mastered).length;
  const mastery = Math.round((current?.p_known ?? 0) * 100);
  const note = notes[selected];
  const shortcuts = [
    {
      id: "reviews",
      icon: RotateCcw,
      title: j.reviewTitle,
      body: j.reviewBody,
      metric: `${cardCount} ${j.cardUnit}`,
    },
    {
      id: "notes",
      icon: NotebookPen,
      title: j.notesTitle,
      body: j.notesBody,
      metric: `${Object.keys(notes).length} ${j.noteUnit}`,
    },
    {
      id: "practice",
      icon: Code2,
      title: j.practiceTitle,
      body: j.practiceBody,
      metric: "Python",
    },
    {
      id: "calendar",
      icon: CalendarDays,
      title: j.calendarTitle,
      body: j.calendarBody,
      metric: t.nav.reviews,
    },
  ] as const;
  return (
    <div className="journal-overview">
      <div className="journal-masthead">
        <span>
          <span className="journal-dot" />
          {j.issue}
        </span>
        <span>{j.edition}</span>
        <span className="journal-edition">NT / 01</span>
      </div>
      <header className="journal-intro">
        <h1>
          {j.headline}
          <br />
          <em>{j.headlineAccent}</em>
          <svg
            className="journal-underline"
            viewBox="0 0 310 14"
            aria-hidden="true"
          >
            <path d="M3 9Q145-2 305 5M30 13Q174 3 285 9" />
          </svg>
        </h1>
        <div className="journal-intro-aside">
          <p>{j.intro}</p>
          <button className="journal-new-path" onClick={onNewTopic}>
            <Plus size={16} />
            {j.newPath}
            <ArrowRight size={15} />
          </button>
        </div>
      </header>

      <div className="journal-spread">
        <section className="journal-atlas" aria-label={j.canvasLabel}>
          <div className="atlas-binding" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
          <header className="atlas-header">
            <div className="atlas-heading">
              <span className="journal-section-number">01</span>
              <div>
                <p className="journal-kicker">{j.chapter}</p>
                <h2>{subject}</h2>
              </div>
            </div>
            <button
              className="atlas-expand"
              onClick={() => onNavigate("map")}
              aria-label={t.viewMap}
            >
              <Compass size={20} />
            </button>
          </header>
          <div className="atlas-caption">
            <h3>{j.mapTitle}</h3>
            <p>{j.mapSubtitle}</p>
          </div>
          <div className="atlas-canvas">
            <svg
              className="atlas-compass"
              viewBox="0 0 60 60"
              aria-hidden="true"
            >
              <circle cx="30" cy="30" r="23" />
              <path d="M30 1v58M1 30h58M17 17l26 26M43 17 17 43" />
              <path d="m30 16 5 14-5 14-5-14Z" />
            </svg>
            {loading ? (
              <Loading />
            ) : error ? (
              <ErrorState error={error} onRetry={onRetry} />
            ) : graph.nodes.length ? (
              <KnowledgeMap
                graph={graph}
                selected={selected}
                onSelect={onSelect}
                variant="atlas"
              />
            ) : (
              <div className="journal-map-empty">
                <Sena size={130} mood="think" />
                <p>{j.empty}</p>
                <Button variant="secondary" onClick={onNewTopic}>
                  {j.newPath}
                </Button>
              </div>
            )}
          </div>
          <footer className="atlas-footer">
            <div className="atlas-legend">
              {j.legend.map((label, i) => (
                <span key={label}>
                  <i className={`atlas-legend-${i}`} />
                  {label}
                </span>
              ))}
            </div>
            <span className="atlas-page-number">
              01 — {String(graph.nodes.length).padStart(2, "0")}
            </span>
          </footer>
          <div className="atlas-progress-caption">
            <span>
              <b>{mastered}</b> / {graph.nodes.length} {j.mastered}
            </span>
            <span>{j.mapHelp}</span>
          </div>
        </section>

        <aside className="journal-guide">
          <div className="guide-tab">
            <BookOpen size={14} />
            {j.guide}
          </div>
          <div className="guide-illustration">
            <div className="guide-halo" />
            <span className="guide-handwriting">{j.quiet}</span>
            <Sena size={220} mood={current?.mastered ? "happy" : "think"} />
            <svg className="guide-spark" viewBox="0 0 40 40" aria-hidden="true">
              <path d="M20 2v36M2 20h36M7 7l26 26M33 7 7 33" />
            </svg>
          </div>
          <div className="guide-message">
            <p className="journal-kicker">{j.next}</p>
            <h2>
              {current ? (
                <>
                  {j.guideIntro}
                  <br />
                  <em>{current.name_vi}.</em>
                </>
              ) : (
                j.empty
              )}
            </h2>
            <p>{current?.mastered ? j.readyBody : j.guideBody}</p>
          </div>
          {current && (
            <div className="guide-mastery">
              <div>
                <span>{j.understanding}</span>
                <strong>
                  {mastery}
                  <small>%</small>
                </strong>
              </div>
              <div
                className="guide-mastery-track"
                role="progressbar"
                aria-label={j.understanding}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={mastery}
              >
                <span style={{ width: `${mastery}%` }} />
              </div>
            </div>
          )}
          <Button
            className="journal-study-button"
            disabled={!current}
            onClick={() => onNavigate("learn")}
          >
            {!approved && mock ? j.approveFirst : j.start}
            <ArrowRight size={17} />
          </Button>
          <button className="journal-why" disabled={!current} onClick={onWhy}>
            {j.why}
            <ChevronUp size={13} />
          </button>
          {note && (
            <blockquote className="guide-personal-note">
              <span>{j.notesPrefix}</span>
              <p>{note}</p>
            </blockquote>
          )}
        </aside>
      </div>

      {mock && (
        <section className="journal-shelf">
          <header>
            <h2>{j.shelf}</h2>
            <span>02 — 05</span>
          </header>
          <div className="journal-shortcuts">
            {shortcuts.map(({ id, icon: Icon, title, body, metric }, i) => (
              <button key={id} onClick={() => onNavigate(id)}>
                <div className="shortcut-top">
                  <span className="shortcut-icon">
                    <Icon size={21} strokeWidth={1.5} />
                  </span>
                  <span className="shortcut-number">0{i + 2}</span>
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
                <div className="shortcut-bottom">
                  <span>{metric}</span>
                  <ArrowRight size={16} />
                </div>
              </button>
            ))}
          </div>
        </section>
      )}
      <p className="journal-closing">
        {j.footer}
        <span aria-hidden="true">✳</span>
      </p>
    </div>
  );
}
