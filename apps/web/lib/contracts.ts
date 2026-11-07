import type { components } from "./api.generated";

// Generated from the integrated FastAPI app; runtime decoders still validate responses.
type Schemas = components["schemas"];
export type GraphNode = Schemas["GraphNode"];
export type KnowledgeGraph = Schemas["GraphView"];
export type DecisionTrace = Schemas["DecisionTrace"];
export type PublicItem = Schemas["PublicItem"];
export type TopicRequest = Schemas["TopicInput"];
export type Tier = TopicRequest["tier"];
export type ResearchMode = TopicRequest["mode"];
export type Citation = Schemas["Citation"];
export type UploadResult = Schemas["UploadResponse"];
export type Placement = Schemas["PlacementStep"];
export type AttemptResult = Schemas["AttemptResult"];
export type HintResult = Schemas["HintResponse"];
export type ReviewCard = Schemas["DueCard"];

export type Source = Schemas["TopicSource"];
export type TopicSnapshot = Schemas["TopicState"];
