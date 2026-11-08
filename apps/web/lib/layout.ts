import dagre from "@dagrejs/dagre";
import type { KnowledgeGraph } from "./contracts";
export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 96;

export function layoutGraph(graph: KnowledgeGraph) {
  const layout = new dagre.graphlib.Graph();
  layout.setGraph({
    rankdir: "LR",
    nodesep: 38,
    ranksep: 62,
    marginx: 28,
    marginy: 28,
  });
  layout.setDefaultEdgeLabel(() => ({}));
  graph.nodes.forEach((node) =>
    layout.setNode(node.slug, {
      width: NODE_WIDTH,
      height: Math.max(
        NODE_HEIGHT,
        80 + Math.ceil((node.name_vi || node.slug).length / 22) * 16,
      ),
    }),
  );
  graph.edges.forEach((edge) => layout.setEdge(edge.from, edge.to));
  dagre.layout(layout);
  return graph.nodes.map((node) => {
    const position = layout.node(node.slug);
    return {
      ...node,
      height: position.height,
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - position.height / 2,
      },
    };
  });
}
