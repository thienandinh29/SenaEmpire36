"use client";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import Image from "next/image";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  type NodeProps,
  type Node,
  MarkerType,
  useReactFlow,
  useNodesInitialized,
  useStore,
} from "@xyflow/react";
import { Check, LockKeyhole } from "lucide-react";
import { layoutGraph, NODE_WIDTH, NODE_HEIGHT } from "@/lib/layout";
import type { KnowledgeGraph } from "@/lib/contracts";
import { vi } from "@/messages/vi";
import { journal as j } from "@/messages/journal";

type ConceptNode = Node<
  {
    label: string;
    mastery: number;
    mastered: boolean;
    active: boolean;
    order: number;
  },
  "concept"
>;
function Concept({ data }: NodeProps<ConceptNode>) {
  return (
    <div
      className={`concept-node ${data.mastered ? "is-mastered" : data.active ? "is-active" : "is-pending"} ${data.active ? "is-current" : ""}`}
      style={
        {
          "--node-progress": `${Math.round(data.mastery * 100)}%`,
        } as CSSProperties
      }
    >
      <Handle type="target" position={Position.Left} />
      <span className="concept-stamp" aria-hidden="true">
        <span>
          {data.mastered ? (
            <Check size={19} strokeWidth={2} />
          ) : data.mastery < 0.2 ? (
            <LockKeyhole size={17} strokeWidth={1.5} />
          ) : (
            String(data.order).padStart(2, "0")
          )}
        </span>
      </span>
      <strong title={data.label}>{data.label}</strong>
      <span className="concept-node-top">
        {Math.round(data.mastery * 100)}% <span aria-hidden="true">·</span>{" "}
        {data.active
          ? j.current
          : data.mastered
            ? j.legend[0]
            : data.mastery < 0.2
              ? j.legend[2]
              : j.legend[1]}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { concept: Concept };
export function KnowledgeMap({
  graph,
  selected,
  onSelect,
  variant = "default",
}: {
  graph: KnowledgeGraph;
  selected: string;
  onSelect: (slug: string) => void;
  variant?: "default" | "atlas";
}) {
  const nodes = useMemo<ConceptNode[]>(
    () =>
      layoutGraph(graph).map((node, index) => ({
        id: node.slug,
        type: "concept",
        position: node.position,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        selected: node.slug === selected,
        domAttributes: { "aria-roledescription": vi.graph.nodeDescription },
        data: {
          label: node.name_vi || node.slug,
          mastery: node.p_known,
          mastered: node.mastered,
          active: node.slug === selected,
          order: index + 1,
        },
        ariaLabel: `${node.name_vi}, ${Math.round(node.p_known * 100)}%`,
      })),
    [graph, selected],
  );
  const edges = useMemo(
    () =>
      graph.edges.map((edge) => ({
        id: `${edge.from}-${edge.to}`,
        source: edge.from,
        target: edge.to,
        type: "default",
        animated: edge.to === selected,
        className: edge.to === selected ? "trail-edge-current" : "trail-edge",
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#b1a2c4",
          width: 14,
          height: 14,
        },
        style: {
          stroke: "var(--trail-edge, #b6aaa0)",
          strokeWidth: 1.5,
          strokeDasharray: "4 6",
        },
        ariaLabel: `${vi.graph.edge}: ${edge.from} → ${edge.to}`,
        domAttributes: { "aria-roledescription": vi.graph.edgeDescription },
      })),
    [graph, selected],
  );
  if (!graph.nodes.length)
    return (
      <div className="knowledge-map empty-map">
        <Image src="/sena.svg" alt="" width={85} height={85} />
        <h3>{vi.flow.emptyGraph}</h3>
        <p>{vi.flow.emptyGraphBody}</p>
      </div>
    );
  return (
    <div
      className={`knowledge-map ${variant === "atlas" ? "knowledge-map-atlas" : ""}`}
      role="region"
      aria-label={vi.mapLabel}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView={variant !== "atlas"}
        fitViewOptions={{ padding: 0.13 }}
        minZoom={0.25}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelect(node.id)}
        onKeyDown={(event) => {
          if (
            (event.key === "Enter" || event.key === " ") &&
            event.target instanceof HTMLElement
          ) {
            const id = event.target
              .closest(".react-flow__node")
              ?.getAttribute("data-id");
            if (id) {
              event.preventDefault();
              onSelect(id);
            }
          }
        }}
        proOptions={{ hideAttribution: false }}
        ariaLabelConfig={{
          "controls.zoomIn.ariaLabel": vi.graph.zoomIn,
          "controls.zoomOut.ariaLabel": vi.graph.zoomOut,
          "controls.fitView.ariaLabel": vi.graph.fit,
          "controls.ariaLabel": vi.graph.controls,
          "node.a11yDescription.default": vi.graph.instructions,
          "node.a11yDescription.keyboardDisabled": vi.graph.instructions,
          "edge.a11yDescription.default": vi.graph.edgeInstructions,
          "node.a11yDescription.ariaLiveMessage": () => vi.graph.selected,
          "handle.ariaLabel": vi.graph.edge,
        }}
      >
        <Background color="var(--atlas-grid-dot, #d9d0c0)" gap={24} size={1} />
        <Controls showInteractive={false} />
        {variant === "atlas" && <AtlasLens graph={graph} selected={selected} />}
      </ReactFlow>
    </div>
  );
}

function AtlasLens({
  graph,
  selected,
}: {
  graph: KnowledgeGraph;
  selected: string;
}) {
  const [whole, setWhole] = useState(false);
  const { fitView } = useReactFlow();
  const ready = useNodesInitialized();
  const width = useStore((state) => state.width);
  const targets = useMemo(() => {
    if (whole) return graph.nodes.map((node) => ({ id: node.slug }));
    const near = new Set([selected]);
    graph.edges.forEach((edge) => {
      if (edge.to === selected) near.add(edge.from);
    });
    return graph.nodes
      .filter((node) => near.has(node.slug))
      .map((node) => ({ id: node.slug }));
  }, [graph, selected, whole]);
  useEffect(() => {
    if (!ready || !width || !targets.length) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const small = width < 480;
    void fitView({
      nodes: small && !whole ? [{ id: selected }] : targets,
      padding: whole ? 0.2 : 0.25,
      maxZoom: 1.15,
      duration: reduced ? 0 : 350,
    });
  }, [ready, width, targets, fitView, whole, selected]);
  return (
    <div
      className="atlas-lens nodrag nopan"
      role="group"
      aria-label={j.canvasLabel}
    >
      <button
        aria-pressed={!whole}
        className={!whole ? "active" : ""}
        onClick={() => setWhole(false)}
      >
        {j.focus}
      </button>
      <button
        aria-pressed={whole}
        className={whole ? "active" : ""}
        onClick={() => setWhole(true)}
      >
        {j.fullMap}
      </button>
    </div>
  );
}
