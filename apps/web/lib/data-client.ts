import type {
  AttemptResult,
  HintResult,
  KnowledgeGraph,
  Placement,
  ReviewCard,
  TopicRequest,
  TopicSnapshot,
  UploadResult,
  Tier,
  PublicItem,
} from "./contracts";
import type { GraphReview } from "./decode";
import type { WebConfig } from "./config";
import { vi as t } from "@/messages/vi";
import {
  DataError,
  parseAttempt,
  parseGraph,
  parseGraphReview,
  parseItem,
  parseHint,
  parsePlacement,
  parseReviews,
  parseTopic,
  parseUpload,
  record,
  string,
} from "./decode";

export interface LearningClient {
  learner(signal?: AbortSignal): Promise<string>;
  upload(
    file: File,
    consentAccepted: boolean,
    signal?: AbortSignal,
    goal?: string,
  ): Promise<UploadResult>;
  createTopic(
    input: TopicRequest,
    signal?: AbortSignal,
  ): Promise<{ topic_id: string; cached: boolean }>;
  topic(id: string, signal?: AbortSignal): Promise<TopicSnapshot>;
  review(
    learner: string,
    subject: string,
    signal?: AbortSignal,
  ): Promise<GraphReview>;
  confirm(
    subject: string,
    revision: string,
    signal?: AbortSignal,
  ): Promise<void>;
  nextItem(
    learner: string,
    subject: string,
    signal?: AbortSignal,
  ): Promise<{ item: PublicItem; reason_vi: string }>;
  graph(
    learner: string,
    subject: string,
    signal?: AbortSignal,
  ): Promise<KnowledgeGraph>;
  placement(
    learner: string,
    subject: string,
    slug: string,
    signal?: AbortSignal,
  ): Promise<Placement>;
  attempt(
    learner: string,
    item: PublicItem,
    slug: string,
    answer: number,
    hints: number,
    signal?: AbortSignal,
  ): Promise<AttemptResult>;
  hint(
    learner: string,
    item: PublicItem,
    slug: string,
    level: number,
    tier: Tier,
    signal?: AbortSignal,
  ): Promise<HintResult>;
  reviews(learner: string, signal?: AbortSignal): Promise<ReviewCard[]>;
}

export function createLearningClient(config: WebConfig): LearningClient {
  const attemptIds = new WeakMap<PublicItem, string>();
  async function request(
    path: string,
    init: RequestInit = {},
  ): Promise<unknown> {
    try {
      const timeout = AbortSignal.timeout(25000);
      const response = await fetch(`/api/backend/${path}`, {
        ...init,
        cache: "no-store",
        signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
      });
      if (!response.ok) {
        let detail: string | undefined;
        try {
          const body = await response.json();
          detail =
            typeof body.detail === "string"
              ? body.detail
              : typeof body.detail?.message === "string"
                ? body.detail.message
                : undefined;
        } catch {
          /* Some proxy failures have no JSON body. */
        }
        throw new DataError(
          response.status === 503 ? "configuration" : "failed",
          response.status,
          detail,
        );
      }
      return await response.json();
    } catch (error) {
      if (
        error instanceof DataError ||
        (error instanceof DOMException && error.name === "AbortError")
      )
        throw error;
      throw new DataError("network");
    }
  }
  const post = (path: string, data: unknown, signal?: AbortSignal) =>
    request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal,
    });
  return {
    async learner(signal) {
      return string(
        record(await post("learners", { display_name: t.learner }, signal))
          .learner_id,
      );
    },
    async upload(file, consentAccepted, signal, goal) {
      if (!consentAccepted || !config.uploadField || !config.uploadMaxBytes)
        throw new DataError("configuration");
      const form = new FormData();
      form.append(config.uploadField, file);
      return parseUpload(
        await request(
          "uploads" + (goal ? `?goal=${encodeURIComponent(goal)}` : ""),
          {
            method: "POST",
            body: form,
            headers: { "X-Demo-Upload-Consent": "demo-v1" },
            signal,
          },
        ),
      );
    },
    async createTopic(input, signal) {
      const d = record(await post("topics", input, signal));
      if (typeof d.cached !== "boolean") throw new DataError("contract");
      return { topic_id: string(d.topic_id), cached: d.cached };
    },
    async topic(id, signal) {
      return parseTopic(
        await request(`topics/${encodeURIComponent(id)}`, { signal }),
      );
    },
    async graph(learner_id, subject, signal) {
      return parseGraph(
        await request(`graph?${new URLSearchParams({ learner_id, subject })}`, {
          signal,
        }),
      );
    },
    async review(learner_id, subject, signal) {
      const raw = await request(
        `graph/review?${new URLSearchParams({ subject })}`,
        { signal },
      );
      const graph = await this.graph(learner_id, subject, signal);
      return parseGraphReview(raw, graph, learner_id, subject);
    },
    async confirm(subject, graph_revision, signal) {
      const value = record(
        await post("graph/confirm", { subject, graph_revision }, signal),
      );
      if (
        value.confirmed !== true ||
        value.subject !== subject ||
        value.graph_revision !== graph_revision
      )
        throw new DataError("contract");
    },
    async nextItem(learner_id, subject, signal) {
      const value = record(
        await request(
          `next-item?${new URLSearchParams({ learner_id, subject })}`,
          { signal },
        ),
      );
      return {
        item: parseItem(value.item),
        reason_vi: string(value.reason_vi),
      };
    },
    async placement(learner_id, subject, _slug, signal) {
      return parsePlacement(
        await post("placement/next", { learner_id, subject }, signal),
      );
    },
    async attempt(learner_id, item, _slug, answer, hints_used, signal) {
      if (!config.answerEncoding) throw new DataError("configuration");
      if (!attemptIds.has(item)) attemptIds.set(item, crypto.randomUUID());
      const result = parseAttempt(
        await post(
          "attempts",
          {
            learner_id,
            item_id: item.id,
            client_attempt_id: attemptIds.get(item),
            answer:
              config.answerEncoding === "index0"
                ? answer
                : item.options[answer]?.label,
            hints_used,
          },
          signal,
        ),
      );
      attemptIds.delete(item);
      return result;
    },
    async hint(learner_id, item, _slug, level, tier, signal) {
      if (config.hintFirstLevel === null) throw new DataError("configuration");
      return parseHint(
        await post(
          "tutor/hint",
          {
            learner_id,
            item_id: item.id,
            level: config.hintFirstLevel + level,
            tier,
          },
          signal,
        ),
      );
    },
    async reviews(learner_id, signal) {
      return parseReviews(
        await request(`reviews/due?${new URLSearchParams({ learner_id })}`, {
          signal,
        }),
      );
    },
  };
}
