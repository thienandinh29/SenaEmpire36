"use client";

import type { KnowledgeGraph } from "@/lib/contracts";
import { Button } from "./ui/button";

export function AdaptiveReview({
  graph,
  disabled,
  onStart,
}: {
  graph: KnowledgeGraph;
  disabled: boolean;
  onStart: () => void;
}) {
  const nodes = new Map(graph.nodes.map((node) => [node.slug, node]));
  function weakFoundation(slug: string) {
    const seen = new Set<string>([slug]);
    const queue = [slug];
    for (let index = 0; index < queue.length; index++) {
      for (const edge of graph.edges) {
        if (edge.to === queue[index] && !seen.has(edge.from)) {
          seen.add(edge.from);
          queue.push(edge.from);
        }
      }
    }
    return queue
      .slice(1)
      .map((id) => nodes.get(id)!)
      .filter((node) => node && node.p_known < 0.5)
      .sort((a, b) => a.p_known - b.p_known)[0];
  }
  return (
    <section className="panel">
      <h2>Ôn tập theo mức hiểu hiện tại</h2>
      <p>
        Mức hiểu ước tính lấy từ biểu đồ và cập nhật sau mỗi câu trả lời. Dưới
        50%: củng cố kiến thức nền; từ 50% đến dưới 95%: luyện tiếp; từ 95%: ôn
        khi đến hạn. Kiến thức mới được mở khi nền liên quan đủ vững.
      </p>
      <Button disabled={disabled || !graph.nodes.length} onClick={onStart}>
        Bắt đầu ôn tập thích ứng
      </Button>
      {!graph.nodes.length && (
        <p>Hãy tạo và xác nhận bản đồ kiến thức để bắt đầu.</p>
      )}
      <div className="review-concepts">
        {graph.nodes.map((node) => {
          const foundation = weakFoundation(node.slug);
          return (
            <article key={node.slug} className="review-concept">
              <h3>{node.name_vi || node.slug}</h3>
              <p>
                {Math.round(node.p_known * 100)}% ·{" "}
                {foundation
                  ? "Cần củng cố kiến thức nền"
                  : node.p_known < 0.5
                    ? "Cần khám phá hoặc củng cố"
                    : node.p_known < 0.95
                      ? "Tiếp tục luyện tập"
                      : "Ôn duy trì"}
              </p>
              <progress
                value={node.p_known}
                max={1}
                aria-label={`Mức hiểu ${node.name_vi}`}
              />
              {foundation && (
                <p>
                  Ôn «{foundation.name_vi}» (
                  {Math.round(foundation.p_known * 100)}%) trước khi quay lại
                  phần này.
                </p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
