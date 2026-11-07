"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { WebConfig } from "@/lib/config";
import { createLearningClient } from "@/lib/data-client";
import type {
  AttemptResult,
  DecisionTrace,
  HintResult,
  KnowledgeGraph,
  PublicItem,
  ReviewCard,
  TopicRequest,
  TopicSnapshot,
  Tier,
} from "@/lib/contracts";
import {
  DataError,
  type GraphReview,
  type ReviewedConcept,
} from "@/lib/decode";

interface Lesson {
  item: PublicItem;
  answer: number | null;
  answerCommitted: boolean;
  result: AttemptResult | null;
  hints: HintResult[];
  reason: string;
  concept: string | null;
}
const emptyGraph: KnowledgeGraph = { nodes: [], edges: [] };
const sessionKey = "nodetrail-live-session";

export function useLearning(config: WebConfig) {
  const client = useMemo(() => createLearningClient(config), [config]);
  const [graph, setGraph] = useState(emptyGraph);
  const [concepts, setConcepts] = useState<ReviewedConcept[]>([]);
  const [selected, setSelected] = useState("");
  const [learner, setLearner] = useState("");
  const [subject, setSubject] = useState("");
  const [topicId, setTopicId] = useState("");
  const [snapshot, setSnapshot] = useState<TopicSnapshot | null>(null);
  const [revision, setRevision] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [placementDone, setPlacementDone] = useState(false);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [traces, setTraces] = useState<DecisionTrace[]>([]);
  const [reviews, setReviews] = useState<ReviewCard[]>([]);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, unknown>>({});
  const [pollVersion, setPollVersion] = useState(0);
  const epoch = useRef(0);
  const locks = useRef(new Set<string>());

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(sessionKey) || "null");
      if (
        saved &&
        typeof saved.learner === "string" &&
        typeof saved.topicId === "string" &&
        /^[a-f0-9-]{36}$/i.test(saved.learner) &&
        /^[a-f0-9-]{36}$/i.test(saved.topicId)
      ) {
        setLearner(saved.learner);
        setTopicId(saved.topicId);
      }
    } catch {
      /* Browser storage is optional. */
    }
  }, []);

  function error(key: string, value: unknown = null) {
    setErrors((all) => ({ ...all, [key]: value }));
  }
  async function run<T>(
    key: string,
    task: () => Promise<T>,
  ): Promise<T | undefined> {
    if (locks.current.has(key)) return;
    locks.current.add(key);
    const version = epoch.current;
    setBusy((all) => ({ ...all, [key]: true }));
    error(key);
    try {
      return await task();
    } catch (caught) {
      if (version === epoch.current) {
        error(key, caught);
        if (caught instanceof DataError && caught.status === 409) {
          setConfirmed(false);
          setLesson(null);
        }
        if (caught instanceof DataError && caught.status === 401) {
          setLearner("");
          setTopicId("");
          setConfirmed(false);
          setLesson(null);
          try {
            localStorage.removeItem(sessionKey);
          } catch {
            /* Browser storage is optional. */
          }
        }
      }
    } finally {
      locks.current.delete(key);
      setBusy((all) => ({ ...all, [key]: false }));
    }
  }
  const applyReview = useCallback((review: GraphReview) => {
    setGraph(review.graph);
    setConcepts(review.concepts);
    setRevision(review.revision);
    setConfirmed(review.confirmed);
    setSelected((slug) =>
      review.graph.nodes.some((n) => n.slug === slug)
        ? slug
        : review.graph.nodes[0]?.slug || "",
    );
  }, []);
  async function createTopic(input: TopicRequest) {
    return run("create", async () => {
      const id = learner || (await client.learner());
      setLearner(id);
      const result = await client.createTopic(input);
      epoch.current++;
      setTopicId(result.topic_id);
      setPollVersion((value) => value + 1);
      setSnapshot(null);
      setSubject("");
      setGraph(emptyGraph);
      setConcepts([]);
      setSelected("");
      setRevision("");
      setConfirmed(false);
      setPlacementDone(false);
      setLesson(null);
      setTraces([]);
      setReviews([]);
      setErrors({});
      try {
        localStorage.setItem(
          sessionKey,
          JSON.stringify({ learner: id, topicId: result.topic_id }),
        );
      } catch {
        /* Browser storage is optional. */
      }
      return result;
    });
  }
  useEffect(() => {
    if (!topicId || !learner) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    async function poll() {
      setBusy((all) => ({ ...all, research: true }));
      try {
        if (Date.now() - started > 10 * 60 * 1000)
          throw new DataError(
            "failed",
            undefined,
            "Tác vụ chưa hoàn tất sau 10 phút. Dữ liệu được giữ; hãy kiểm tra và thử lại.",
          );
        const next = await client.topic(topicId, controller.signal);
        if (controller.signal.aborted) return;
        setSnapshot(next);
        setErrors((all) => ({ ...all, research: null }));
        if (next.status === "failed") throw new DataError("failed");
        if (next.status !== "ready") {
          timer = setTimeout(poll, 2500);
          return;
        }
        if (!next.subject_slug || !next.graph_ready || !next.items_ready)
          throw new DataError("contract");
        const review = await client.review(
          learner,
          next.subject_slug,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setSubject(next.subject_slug);
        applyReview(review);
      } catch (caught) {
        if (!controller.signal.aborted)
          setErrors((all) => ({ ...all, research: caught }));
      } finally {
        if (!controller.signal.aborted)
          setBusy((all) => ({ ...all, research: false }));
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [client, learner, topicId, pollVersion, applyReview]);

  async function reloadGraph() {
    if (!subject || !learner) return;
    await run("graph", async () => {
      const version = epoch.current;
      const review = await client.review(learner, subject);
      if (version === epoch.current) {
        applyReview(review);
        if (!review.confirmed) setLesson(null);
      }
    });
  }
  async function confirmGraph() {
    if (!subject || !revision || confirmed) return;
    const version = epoch.current;
    await run("confirm", async () => {
      await client.confirm(subject, revision);
      if (version === epoch.current) setConfirmed(true);
    });
    await reloadGraph();
  }
  async function loadLesson() {
    if (
      !confirmed ||
      !learner ||
      !subject ||
      locks.current.has("attempt") ||
      locks.current.has("hint")
    )
      return;
    await run("lesson", async () => {
      const version = epoch.current;
      let done = placementDone;
      if (!done) {
        const step = await client.placement(learner, subject, selected);
        if (version !== epoch.current) return;
        setTraces((all) => [...all, step.trace]);
        done = step.done;
        setPlacementDone(done);
        if (step.item) {
          setLesson({
            item: step.item,
            answer: null,
            answerCommitted: false,
            result: null,
            hints: [],
            reason: step.trace.rule_vi,
            concept: step.trace.concept_slug,
          });
          setSelected(step.trace.concept_slug);
          return;
        }
      }
      if (done) {
        const next = await client.nextItem(learner, subject);
        if (version === epoch.current)
          setLesson({
            item: next.item,
            answer: null,
            answerCommitted: false,
            result: null,
            hints: [],
            reason: next.reason_vi,
            concept: null,
          });
      }
    });
  }
  function setAnswer(answer: number) {
    setLesson((current) =>
      current && !current.result && !current.answerCommitted
        ? { ...current, answer }
        : current,
    );
  }
  async function attempt() {
    if (!lesson || lesson.answer === null || lesson.result) return;
    const current = lesson;
    setLesson((value) =>
      value?.item === current.item
        ? { ...value, answerCommitted: true }
        : value,
    );
    await run("attempt", async () => {
      const version = epoch.current;
      const result = await client.attempt(
        learner,
        current.item,
        current.concept || "",
        current.answer!,
        current.hints.length,
      );
      if (version !== epoch.current) return;
      setLesson((value) =>
        value?.item === current.item ? { ...value, result } : value,
      );
      setTraces((all) => [...all, ...result.traces]);
      const graded = result.traces
        .filter((trace) => trace.kind === "bkt_update")
        .at(-1)?.concept_slug;
      if (graded) setSelected(graded);
      await reloadGraph();
    });
  }
  async function hint(tier: Tier) {
    if (!lesson || lesson.hints.length >= 3) return;
    const current = lesson;
    await run("hint", async () => {
      const version = epoch.current;
      const response = await client.hint(
        learner,
        current.item,
        current.concept || "",
        current.hints.length,
        tier,
      );
      if (!response.hint_vi.trim() || !response.citations.length)
        throw new DataError("contract");
      if (version === epoch.current)
        setLesson((value) =>
          value?.item === current.item
            ? { ...value, hints: [...value.hints, response] }
            : value,
        );
    });
  }
  async function loadReviews() {
    if (!learner) return;
    await run("reviews", async () => {
      const version = epoch.current;
      const cards = await client.reviews(learner);
      if (version === epoch.current) setReviews(cards);
    });
  }
  return {
    graph,
    concepts,
    selected,
    setSelected,
    subject,
    topicId,
    snapshot,
    confirmed,
    placementDone,
    lesson,
    traces,
    reviews,
    busy,
    errors,
    createTopic,
    upload: (file: File, consent: boolean, goal?: string) =>
      run("upload", () => client.upload(file, consent, undefined, goal)),
    reloadGraph,
    confirmGraph,
    loadLesson,
    setAnswer,
    attempt,
    hint,
    loadReviews,
    retryResearch: () => setPollVersion((n) => n + 1),
  };
}
