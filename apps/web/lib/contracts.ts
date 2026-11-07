import type { components } from "./api.generated";

// Wire shapes generated from the integrated app; decoders still validate runtime data.
export type GraphNode = components["schemas"]["GraphNode"];
export type KnowledgeGraph = components["schemas"]["GraphResponse"];
export interface DecisionTrace {
  kind: "bkt_update" | "placement_step" | "root_cause" | "next_item" | "review";
  concept_slug: string;
  at: string;
  prior: number | null;
  evidence: {
    item_id?: string;
    correct?: boolean;
    misconception?: string;
    slip?: number;
    guess?: number;
  };
  posterior: number | null;
  rule: string;
  rule_vi: string;
  alternatives: { concept_slug: string; p_known: number; why_not_vi: string }[];
}
export type PublicItem = components["schemas"]["LearnerItem"];

export type Tier = "free" | "pro";
export type ResearchMode = "quick" | "deep";
export interface TopicRequest {
  goal_vi?: string;
  upload_id?: string;
  mode: ResearchMode;
  tier: Tier;
}
export interface Source {
  title: string;
  publisher: string;
  url: string;
  license: string;
}
export interface Citation {
  title: string;
  section: string;
  url: string;
}
export interface TopicSnapshot {
  status:
    | "queued"
    | "researching"
    | "indexing"
    | "graph"
    | "items"
    | "ready"
    | "failed";
  step_vi: string;
  progress: number;
  subject_slug?: string;
  graph_ready: boolean;
  items_ready: boolean;
  sources: Source[];
  trail: {
    at: string;
    kind: "search" | "read" | "select";
    text_vi: string;
    url?: string;
  }[];
}
export interface UploadResult {
  upload_id: string;
  pages: number;
  text_ok: boolean;
}
export interface Placement {
  item: PublicItem | null;
  done: boolean;
  gap_slug?: string;
  trace: DecisionTrace;
}
export interface AttemptResult {
  correct: boolean;
  misconception_vi?: string;
  p_known: number;
  mastered: boolean;
  remediation?: { concept_slug: string; reason_vi: string };
  traces: DecisionTrace[];
}
export interface HintResult {
  hint_vi: string;
  citations: Citation[];
}
export interface ReviewCard {
  concept_slug: string;
  due_at: string;
}
