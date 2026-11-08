import type { KnowledgeGraph } from "@/lib/contracts";
import type { GraphReview } from "@/lib/decode";

export function MasteryChart({
  graph,
  assessment,
}: {
  graph: KnowledgeGraph;
  assessment: GraphReview["assessment"];
}) {
  if (!graph.nodes.length) return null;

  return (
    <section className="mastery-chart" aria-labelledby="mastery-chart-title">
      <header>
        <div>
          <h2 id="mastery-chart-title">Biểu đồ kiến thức của bạn</h2>
          <p>
            Mức độ thành thạo ước tính sau trắc nghiệm, được cập nhật khi bạn
            tiếp tục ôn tập.
          </p>
        </div>
        {assessment && (
          <span className="mastery-chart-count">
            {assessment.answered} câu đã trả lời · {assessment.correct} câu đúng
          </span>
        )}
      </header>
      <ul className="mastery-chart-bars">
        {graph.nodes.map((node) => {
          const percent = Math.round(
            Math.max(0, Math.min(1, node.p_known)) * 100,
          );
          const result = assessment?.concepts.find(
            (entry) => entry.slug === node.slug,
          );
          const unassessed = !result || result.correct + result.incorrect === 0;
          const status = unassessed
            ? "Chưa được kiểm tra trực tiếp"
            : node.mastered
              ? "Đã nắm vững"
              : "Cần củng cố thêm";

          return (
            <li key={node.slug}>
              <div className="mastery-chart-label">
                <span>{node.name_vi}</span>
                <strong>{percent}%</strong>
              </div>
              <div
                className="mastery-chart-track"
                role="meter"
                aria-label={`Mức độ thành thạo: ${node.name_vi}`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
                aria-valuetext={`${percent}% · ${status}`}
                data-mastered={node.mastered}
                data-unassessed={unassessed}
              >
                <span style={{ width: `${percent}%` }} />
              </div>
              <small>{status}</small>
            </li>
          );
        })}
      </ul>
      <p className="mastery-chart-note">
        Thang đo 0–100%. Đây là ước tính mức độ nắm vững từng kiến thức, không
        phải tỷ lệ câu trả lời đúng. Phần chưa được kiểm tra cần thêm câu trả
        lời để đánh giá.
      </p>
    </section>
  );
}
