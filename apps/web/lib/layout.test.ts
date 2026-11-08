import { describe, expect, it } from "vitest";
import { layoutGraph, NODE_WIDTH, NODE_HEIGHT } from "./layout";
import type { KnowledgeGraph } from "./contracts";

describe("dagre map layout", () => {
  for (const size of [1, 7, 30]) {
    it(`lays out a ${size}-concept chain without overlapping nodes`, () => {
      const graph: KnowledgeGraph = {
        nodes: Array.from({ length: size }, (_, i) => ({
          slug: `n${i}`,
          name_vi: `n${i}`,
          p_known: 0,
          mastered: false,
        })),
        edges: Array.from({ length: size - 1 }, (_, i) => ({
          from: `n${i}`,
          to: `n${i + 1}`,
        })),
      };
      const nodes = layoutGraph(graph);
      expect(nodes).toHaveLength(size);
      for (let i = 1; i < nodes.length; i++)
        expect(
          nodes[i].position.x - nodes[i - 1].position.x,
        ).toBeGreaterThanOrEqual(NODE_WIDTH);
    });
  }
  it("keeps branching prerequisites before their descendants", () => {
    const graph: KnowledgeGraph = {
      nodes: ["a", "b", "c", "d"].map((slug) => ({
        slug,
        name_vi: slug,
        p_known: 0,
        mastered: false,
      })),
      edges: [
        { from: "a", to: "b" },
        { from: "a", to: "c" },
        { from: "b", to: "d" },
        { from: "c", to: "d" },
      ],
    };
    const positions = new Map(
      layoutGraph(graph).map((n) => [n.slug, n.position]),
    );
    for (const edge of graph.edges)
      expect(positions.get(edge.to)!.x).toBeGreaterThan(
        positions.get(edge.from)!.x,
      );
    expect(
      Math.abs(positions.get("b")!.y - positions.get("c")!.y),
    ).toBeGreaterThanOrEqual(NODE_HEIGHT);
  });
  it("reserves more height for long Vietnamese labels", () => {
    expect(layoutGraph({ nodes: [], edges: [] })).toEqual([]);
    const nodes = layoutGraph({
      nodes: [
        {
          slug: "long",
          name_vi: "Một khái niệm có nhãn tiếng Việt rất dài ".repeat(20),
          p_known: 0,
          mastered: false,
        },
      ],
      edges: [],
    });
    expect(Number.isFinite(nodes[0].position.x)).toBe(true);
    expect(Number.isFinite(nodes[0].position.y)).toBe(true);
    expect(nodes[0].height).toBeGreaterThan(NODE_HEIGHT);
  });
  it("keeps long labels from overlapping in a large unconnected curriculum", () => {
    const nodes = layoutGraph({
      nodes: Array.from({ length: 40 }, (_, i) => ({
        slug: `rule-${i}`,
        name_vi:
          "Phương pháp quy đồng mẫu số và cộng các phân số khác mẫu ".repeat(3),
        p_known: 0,
        mastered: false,
      })),
      edges: [],
    });
    expect(nodes).toHaveLength(40);
    const sorted = [...nodes].sort((a, b) => a.position.y - b.position.y);
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i].position.y).toBeGreaterThanOrEqual(
        sorted[i - 1].position.y + sorted[i - 1].height,
      );
    }
  });
});
