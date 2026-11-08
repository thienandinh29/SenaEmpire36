"use client";

import { useEffect, useRef, useState } from "react";
import { Dialog } from "radix-ui";
import {
  ArrowRight,
  BookOpen,
  Check,
  Compass,
  GitBranch,
  Layers3,
  Leaf,
  Lightbulb,
  Map,
  Plus,
  RotateCcw,
  Sprout,
  X,
} from "lucide-react";
import { Button } from "./ui/button";
import { Sena } from "./sena";
import { ThemeToggle } from "./theme-toggle";
import { JournalOverview } from "./journal-overview";
import { KnowledgeMap } from "./knowledge-map";
import { SourceLink } from "./source-link";
import { AssessmentReview } from "./assessment-review";
import { AdaptiveReview } from "./adaptive-review";
import { TracePanel } from "./trace-panel";
import { ErrorState, Loading } from "./async-state";
import { useLearning } from "./use-learning";
import type { WebConfig } from "@/lib/config";
import { vi as t } from "@/messages/vi";

type Screen = "overview" | "map" | "learn" | "reviews" | "sources" | "research";
const navigation = [
  { id: "overview", icon: Compass, label: t.nav.overview },
  { id: "map", icon: Map, label: t.nav.map },
  { id: "learn", icon: BookOpen, label: t.nav.learn },
  { id: "reviews", icon: RotateCcw, label: t.nav.reviews },
  { id: "sources", icon: Layers3, label: t.sources },
] as const;

export function Workspace({ config }: { config: WebConfig }) {
  const learning = useLearning(config);
  const { graph, selected, snapshot, lesson, busy, errors, confirmed } =
    learning;
  const [screen, setScreen] = useState<Screen>("overview");
  const [topicOpen, setTopicOpen] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const uploaded = useRef<{ file: File; id: string } | null>(null);
  const creating = useRef(false);
  const [mode, setMode] = useState<"quick" | "deep">("deep");
  const [health, setHealth] = useState<"checking" | "ok" | "error">("checking");
  const [healthVersion, setHealthVersion] = useState(0);
  const [embeddingUnavailable, setEmbeddingUnavailable] = useState<
    string | null
  >(null);
  const mainRef = useRef<HTMLElement>(null);
  const concept = learning.concepts.find((value) => value.slug === selected);
  const sources = snapshot?.sources || [];
  const inFlight = Object.values(busy).some(Boolean);
  const tier = mode === "deep" ? "pro" : "free";

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/backend/health", {
      cache: "no-store",
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        const state: unknown = await response.json();
        setEmbeddingUnavailable(
          state &&
            typeof state === "object" &&
            "embedding" in state &&
            state.embedding !== "ready"
            ? String(state.embedding)
            : null,
        );
        if (
          state &&
          typeof state === "object" &&
          "db" in state &&
          state.db === "ok" &&
          "status" in state &&
          state.status === "ok"
        ) {
          if (!controller.signal.aborted) setHealth("ok");
        } else throw new Error("unavailable");
      })
      .catch(() => {
        if (!controller.signal.aborted) setHealth("error");
      });
    return () => controller.abort();
  }, [healthVersion]);

  function navigate(next: Screen) {
    if (next === "learn" && !confirmed) next = "map";
    setScreen(next);
    mainRef.current?.focus();
    if (next === "reviews") void learning.loadReviews();
    if (next === "learn" && !lesson) void learning.loadLesson();
  }
  async function startResearch() {
    if (
      creating.current ||
      (!goal.trim() && !file) ||
      goal.length > 500 ||
      (file && !consent)
    )
      return;
    creating.current = true;
    try {
      if (file && uploaded.current?.file !== file) {
        const result = await learning.upload(file, consent, goal);
        if (!result || !result.text_ok) return;
        uploaded.current = { file, id: result.upload_id };
      }
      const created = await learning.createTopic({
        goal_vi: goal.trim() ? goal.trim().normalize("NFC") : undefined,
        upload_id: file ? uploaded.current?.id : undefined,
        mode,
        tier,
      });
      if (created) {
        setTopicOpen(false);
        setScreen("research");
      }
    } finally {
      creating.current = false;
    }
  }
  const approval = graph.nodes.length > 0 && (
    <div className={`approval-banner ${confirmed ? "is-approved" : ""}`}>
      <p>{confirmed ? t.live.approved : t.live.approveFirst}</p>
      <Button
        disabled={confirmed || busy.confirm || busy.graph}
        onClick={() => void learning.confirmGraph()}
      >
        <Check size={16} />
        {confirmed ? t.live.approved : t.live.approve}
      </Button>
    </div>
  );

  return (
    <div className="app-shell journal-ui">
      <a className="skip-link" href="#main-content">
        {t.flow.skip}
      </a>
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate("overview")}>
          <span className="brand-symbol">
            <GitBranch size={25} />
          </span>
          {t.app}
          <span className="brand-period">.</span>
        </button>
        <div className="sidebar-caption">{t.workspace}</div>
        <nav className="primary-nav" aria-label={t.workspace}>
          {navigation.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              className={screen === id ? "active" : ""}
              aria-current={screen === id ? "page" : undefined}
              onClick={() => navigate(id)}
            >
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <Button onClick={() => setTopicOpen(true)}>
          <Plus size={16} />
          {t.live.newTopic}
        </Button>
        <div className="sidebar-bottom">
          <div className="sidebar-sena">
            <span>
              <Leaf size={18} />
              {t.tagline}
            </span>
            <p>{t.senaTag}</p>
          </div>
          <div className="profile">
            <span className="avatar">
              <Sprout size={20} />
            </span>
            <div>
              <strong>{t.learner}</strong>
              <small>{t.learnerSub}</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            {t.workspace}
            <strong>
              {navigation.find((n) => n.id === screen)?.label ||
                t.live.research}
            </strong>
          </div>
          <div className="topbar-right">
            <ThemeToggle />
            <span className="pill">{t.live.badge}</span>
            <Button variant="secondary" onClick={() => setTopicOpen(true)}>
              <Plus size={16} />
              {t.newTopic}
            </Button>
          </div>
        </header>
        <main id="main-content" ref={mainRef} tabIndex={-1}>
          <nav className="mobile-resources" aria-label={t.workspace}>
            {navigation.map(({ id, label }) => (
              <button key={id} onClick={() => navigate(id)}>
                {label}
              </button>
            ))}
          </nav>
          <div
            className={health === "error" ? "error-state" : "mode-notice"}
            role="status"
          >
            <p>
              {health === "checking"
                ? t.live.checking
                : health === "ok"
                  ? t.live.connected
                  : embeddingUnavailable
                    ? embeddingUnavailable === "loading"
                      ? t.live.embeddingUnavailable
                      : embeddingUnavailable === "model_mismatch"
                        ? t.live.embeddingMismatch
                        : t.live.embeddingError
                    : t.live.unavailable}
            </p>
            <Button
              variant="ghost"
              onClick={() => {
                setHealth("checking");
                setHealthVersion((v) => v + 1);
              }}
            >
              {t.live.checkConnection}
            </Button>
          </div>
          {learning.topicId && (
            <button
              className="text-button"
              onClick={() => setScreen("research")}
            >
              {t.flow.resume}
              <ArrowRight size={14} />
            </button>
          )}
          <ErrorState
            error={errors.confirm}
            onRetry={() => void learning.reloadGraph()}
          />
          <ErrorState
            error={errors.graph}
            onRetry={() => void learning.reloadGraph()}
          />

          {screen === "overview" && (
            <JournalOverview
              graph={graph}
              selected={selected}
              subject={learning.subject || t.live.noTopic}
              approved={confirmed}
              loading={busy.graph}
              error={errors.graph}
              onSelect={learning.setSelected}
              onRetry={() => void learning.reloadGraph()}
              onNavigate={navigate}
              onNewTopic={() => setTopicOpen(true)}
              onWhy={() => setTraceOpen(true)}
            />
          )}

          {screen === "map" && (
            <>
              <PageHeading
                title={t.nav.map}
                description={`${learning.subject || t.live.noTopic} · ${graph.nodes.length} ${t.conceptCount}`}
              />
              {approval}
              <div className="map-page-grid">
                <section className="panel large-map">
                  <KnowledgeMap
                    graph={graph}
                    selected={selected}
                    onSelect={learning.setSelected}
                  />
                  <Button
                    variant="ghost"
                    disabled={!learning.subject || busy.graph}
                    onClick={() => void learning.reloadGraph()}
                  >
                    {t.flow.reloadGraph}
                  </Button>
                </section>
                <aside className="panel concept-detail">
                  <h2>{concept?.name_vi || t.live.noTopic}</h2>
                  <p>{concept?.description_vi}</p>
                  {!!concept?.pages.length && (
                    <p>Trang {concept.pages.join(", ")}</p>
                  )}
                  {concept?.sources.map((url) => (
                    <SourceLink key={url} url={url} title={t.live.sources} />
                  ))}
                  <Button
                    disabled={!confirmed}
                    onClick={() => navigate("learn")}
                  >
                    {t.start}
                    <ArrowRight size={16} />
                  </Button>
                </aside>
              </div>
            </>
          )}

          {screen === "research" && (
            <>
              <PageHeading
                title={t.live.research}
                description={t.live.researchHelp}
              />
              <section className="panel">
                {busy.research && (
                  <Loading label={snapshot?.step_vi || t.flow.loading} />
                )}
                {snapshot && (
                  <>
                    <p>{snapshot.step_vi}</p>
                    <progress
                      aria-label={t.live.research}
                      max={1}
                      value={snapshot.progress}
                    />
                    <p>{Math.round(snapshot.progress * 100)}%</p>
                    <ol className="research-trail">
                      {snapshot.trail.map((entry, i) => (
                        <li key={`${entry.at}-${i}`}>
                          <p>{entry.text_vi}</p>
                          {entry.url && (
                            <SourceLink
                              url={entry.url}
                              title={t.live.sources}
                            />
                          )}
                        </li>
                      ))}
                    </ol>
                  </>
                )}
                <ErrorState
                  error={errors.research}
                  onRetry={() => {
                    if (snapshot?.status === "failed") {
                      if (goal.trim() || file) void startResearch();
                      else setTopicOpen(true);
                    } else learning.retryResearch();
                  }}
                />
                {learning.subject && snapshot?.status === "ready" && (
                  <>
                    <p>{t.live.published}</p>
                    <Button onClick={() => navigate("map")}>
                      {t.viewMap}
                      <ArrowRight size={16} />
                    </Button>
                  </>
                )}
                {!learning.topicId && (
                  <Button onClick={() => setTopicOpen(true)}>
                    {t.live.newTopic}
                  </Button>
                )}
              </section>
            </>
          )}

          {screen === "learn" && (
            <>
              <PageHeading
                title={
                  learning.reviewMode
                    ? "Ôn tập thích ứng"
                    : learning.completed
                      ? t.live.assessmentTitle
                      : learning.placementDone
                        ? t.live.practice
                        : t.live.start
                }
                description={
                  learning.completed && learning.reviewMode
                    ? "Các kiến thức đã đạt ngưỡng nắm vững. Bạn có thể ôn tiếp khi đến hạn."
                    : learning.completed
                      ? t.live.assessmentHelp
                      : lesson?.reason || t.live.noQuestion
                }
              />
              <div className="learning-grid">
                <section className="panel lesson-panel">
                  {busy.lesson && <Loading />}
                  <ErrorState
                    error={errors.lesson}
                    onRetry={() => void learning.loadLesson()}
                  />
                  {learning.completed && (
                    <section role="status">
                      <h2>
                        {learning.reviewMode
                          ? "Mức hiểu sau ôn tập"
                          : t.live.masterySummary}
                      </h2>
                      {!learning.reviewMode && (
                        <AssessmentReview
                          assessment={learning.assessment}
                          concepts={learning.concepts}
                        />
                      )}
                      {learning.graph.nodes.map((node) => (
                        <p key={node.slug}>
                          {node.name_vi}: {Math.round(node.p_known * 100)}%
                        </p>
                      ))}
                      <Button onClick={() => navigate("reviews")}>
                        {t.live.reviewNext}
                      </Button>
                    </section>
                  )}
                  {!lesson && !learning.completed && (
                    <Button
                      disabled={!confirmed || busy.lesson}
                      onClick={() => void learning.loadLesson()}
                    >
                      {t.live.start}
                    </Button>
                  )}
                  {lesson && (
                    <div className="question">
                      {learning.reviewMode && concept && (
                        <section className="review-concept">
                          <h3>{concept.name_vi}</h3>
                          <p>
                            Mức hiểu hiện tại:{" "}
                            {Math.round(
                              (graph.nodes.find(
                                (node) => node.slug === concept.slug,
                              )?.p_known ?? 0) * 100,
                            )}
                            %
                          </p>
                          <p>{concept.description_vi}</p>
                          {concept.sources.map((url) => (
                            <SourceLink
                              key={url}
                              title="Đọc lại kiến thức từ giáo trình"
                              url={url}
                            />
                          ))}
                        </section>
                      )}
                      <h2>{lesson.item.prompt_vi}</h2>
                      <fieldset
                        disabled={
                          !!lesson.result ||
                          lesson.answerCommitted ||
                          busy.attempt ||
                          busy.lesson
                        }
                      >
                        <legend className="sr-only">{t.answerLabel}</legend>
                        {lesson.item.options.map((option, index) => (
                          <label
                            key={`${lesson.item.id}-${index}`}
                            className={`answer-option ${lesson.answer === index ? "is-selected" : ""}`}
                          >
                            <input
                              type="radio"
                              name={lesson.item.id}
                              checked={lesson.answer === index}
                              onChange={() => learning.setAnswer(index)}
                            />
                            <span className="answer-letter">
                              {String.fromCharCode(65 + index)}
                            </span>
                            <span>{option.label}</span>
                          </label>
                        ))}
                      </fieldset>
                      <div className="question-actions">
                        <Button
                          disabled={
                            lesson.answer === null ||
                            !!lesson.result ||
                            busy.attempt ||
                            busy.lesson ||
                            busy.hint
                          }
                          onClick={() => void learning.attempt()}
                        >
                          {busy.attempt ? t.flow.saving : t.check}
                        </Button>
                        {lesson.result && (
                          <Button
                            disabled={busy.lesson || busy.attempt}
                            onClick={() => void learning.loadLesson()}
                          >
                            {t.live.next}
                            <ArrowRight size={16} />
                          </Button>
                        )}
                      </div>
                      {lesson.result && (
                        <div
                          className={`feedback ${lesson.result.correct ? "correct" : "incorrect"}`}
                          role="status"
                        >
                          <strong>
                            {lesson.result.correct
                              ? t.live.resultCorrect
                              : t.live.resultWrong}
                          </strong>
                          {lesson.result.misconception_vi && (
                            <p>{lesson.result.misconception_vi}</p>
                          )}
                          {lesson.result.remediation && (
                            <p>{lesson.result.remediation.reason_vi}</p>
                          )}
                          <button
                            className="text-button"
                            onClick={() => setTraceOpen(true)}
                          >
                            {t.why}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  <ErrorState
                    error={errors.attempt}
                    onRetry={() => void learning.attempt()}
                  />
                </section>
                <aside className="panel tutor-panel">
                  <Sena size={140} mood={busy.hint ? "think" : "focus"} />
                  <h2>{t.tutorTitle}</h2>
                  <p>{t.tutorSub}</p>
                  {lesson?.hints.map((hint, i) => (
                    <div className="hint-bubble" key={i}>
                      <p>{hint.hint_vi}</p>
                      {hint.citations.map((citation, j) => (
                        <SourceLink
                          key={j}
                          url={citation.url}
                          title={citation.title}
                          section={citation.section || undefined}
                          page={citation.page || undefined}
                        />
                      ))}
                    </div>
                  ))}
                  <Button
                    disabled={
                      !lesson ||
                      busy.hint ||
                      busy.lesson ||
                      busy.attempt ||
                      lesson.hints.length >= 3
                    }
                    onClick={() => void learning.hint(tier)}
                  >
                    <Lightbulb size={16} />
                    {t.hint}
                  </Button>
                  <ErrorState
                    error={errors.hint}
                    onRetry={() => void learning.hint(tier)}
                  />
                </aside>
              </div>
            </>
          )}

          {screen === "reviews" && (
            <>
              <PageHeading
                title={t.nav.reviews}
                description={t.live.reviewsHelp}
              />
              <AdaptiveReview
                graph={graph}
                disabled={!confirmed || inFlight}
                onStart={() => {
                  setScreen("learn");
                  mainRef.current?.focus();
                  void learning.startReview();
                }}
              />
              <AssessmentReview
                assessment={learning.assessment}
                concepts={learning.concepts}
              />
              {busy.reviews && <Loading />}
              <ErrorState
                error={errors.reviews}
                onRetry={() => void learning.loadReviews()}
              />
            </>
          )}

          {screen === "sources" && (
            <>
              <PageHeading title={t.sources} description={t.live.sources} />
              <section className="panel">
                {!sources.length && <p>{t.live.sourcesEmpty}</p>}
                {sources.map((source) => (
                  <article key={source.url}>
                    <SourceLink title={source.title} url={source.url} />
                    <p>
                      {source.publisher} · {source.license}
                    </p>
                  </article>
                ))}
              </section>
            </>
          )}
        </main>
      </div>

      <Dialog.Root open={topicOpen} onOpenChange={setTopicOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content topic-dialog">
            <Dialog.Close className="dialog-close" aria-label={t.close}>
              <X size={20} />
            </Dialog.Close>
            <Dialog.Title>{t.live.title}</Dialog.Title>
            <Dialog.Description>{t.live.intro}</Dialog.Description>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void startResearch();
              }}
            >
              <label className="field-label" htmlFor="goal">
                {t.goal}
              </label>
              <textarea
                id="goal"
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                maxLength={500}
                placeholder={t.placeholder}
                disabled={busy.create}
              />
              <div className="mode-options">
                <button
                  type="button"
                  aria-pressed={mode === "quick"}
                  className={mode === "quick" ? "selected-mode" : ""}
                  onClick={() => setMode("quick")}
                >
                  <strong>{t.quick}</strong>
                  <small>
                    {t.live.quick} · {t.live.standard}
                  </small>
                </button>
                <button
                  type="button"
                  aria-pressed={mode === "deep"}
                  className={mode === "deep" ? "selected-mode" : ""}
                  onClick={() => setMode("deep")}
                >
                  <strong>{t.deep}</strong>
                  <small>
                    {t.live.deep} · {t.live.advanced}
                  </small>
                </button>
              </div>
              <label className="field-label" htmlFor="lesson-file">
                {t.flow.uploadChoose}
              </label>
              <input
                id="lesson-file"
                type="file"
                accept=".pdf,.docx"
                disabled={inFlight}
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  uploaded.current = null;
                }}
              />
              {file && (
                <>
                  <Button
                    variant="ghost"
                    type="button"
                    onClick={() => {
                      setFile(null);
                      setConsent(false);
                      uploaded.current = null;
                    }}
                  >
                    {t.removeFile}
                  </Button>
                  <p className="fine-print">{t.uploadDemoNotice}</p>
                  <label>
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(event) => setConsent(event.target.checked)}
                    />{" "}
                    {t.uploadDemoConsent}
                  </label>
                </>
              )}
              {busy.upload && <Loading label={t.flow.uploading} />}
              <ErrorState error={errors.upload} />
              <ErrorState
                error={errors.create}
                onRetry={() => void startResearch()}
              />
              <p className="fine-print">{t.live.saved}</p>
              <div className="dialog-actions">
                <Button variant="ghost" onClick={() => setTopicOpen(false)}>
                  {t.cancel}
                </Button>
                <Button
                  type="submit"
                  disabled={
                    (!goal.trim() && !file) ||
                    inFlight ||
                    (Boolean(file) && !consent) ||
                    health !== "ok"
                  }
                >
                  {busy.create ? t.live.creating : t.live.newTopic}
                  <ArrowRight size={16} />
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      <Dialog.Root open={traceOpen} onOpenChange={setTraceOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content trace-dialog">
            <Dialog.Close className="dialog-close" aria-label={t.close}>
              <X size={20} />
            </Dialog.Close>
            <Dialog.Title>{t.traceTitle}</Dialog.Title>
            <Dialog.Description>{t.live.traceEmpty}</Dialog.Description>
            {learning.traces.map((trace, i) => (
              <TracePanel key={i} trace={trace} graph={graph} />
            ))}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function PageHeading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page-heading">
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}
