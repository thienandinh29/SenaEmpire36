# NodeTrail · Sena Empire

**Gia sư AI biết bạn đang ở đâu và dẫn bạn đi tiếp.** Sản phẩm dự thi hackathon 2026 của đội Sena Empire.
Linh vật: **Sena**, chú khỉ đồng hành học tập.

Người học nêu một mục tiêu ("Tôi muốn học Python") hoặc tải lên một tệp. NodeTrail dựng bản đồ kiến thức từ giáo trình
tin cậy, xếp trình độ, rồi chạy vòng lặp **đánh giá → học → luyện tập → điều chỉnh → ôn tập**. Mọi giải thích đều có
trích dẫn nguồn.

## Vấn đề

Tỉ lệ hoàn thành trung vị của các khóa học trực tuyến chỉ khoảng 12,6% (Jordan, 2015). Người tự học không biết bắt đầu từ
đâu, học xong là quên, và trợ lý trò chuyện chỉ trả lời từng câu mà không biết nên học gì tiếp.

## Ý tưởng cốt lõi: AI giải thích, bộ máy quyết định

Mô hình ngôn ngữ **không** quyết định bước học tiếp theo. Nó nằm trong một khung kiểm soát:

| Thành phần | Vai trò |
|---|---|
| **Bộ máy học tập** (hàm thuần, có kiểm thử) | Quyết định học gì tiếp: BKT đo mức nắm vững từng khái niệm; luật trên đồ thị tiên quyết xếp trình độ và truy ngược gốc lỗ hổng; FSRS lên lịch ôn |
| **Người chấm khách quan** | Câu trắc nghiệm chấm bằng đáp án, không nhờ mô hình chấm; mỗi đáp án sai gắn một quan niệm sai |
| **Mô hình ngôn ngữ + truy xuất (RAG)** | Chỉ giải thích và tạo nội dung, luôn kèm trích dẫn giáo trình |
| **Cổng kiểm chứng** | Một mô hình khác họ (DeepSeek tạo, Gemini kiểm) trả lời mù từ chính các đoạn đã trích; câu không khớp thì không bao giờ đến tay người học |
| **Bảng «Vì sao?»** | Mỗi quyết định của bộ máy có dấu vết (`DecisionTrace`) bằng tiếng Việt: luật nào chạy, các lựa chọn khác và vì sao bị loại |

Sena chỉ khen khi mức nắm vững tăng thật, không khen vì nhanh hay vì chuỗi ngày. Nội dung do AI tạo mang nhãn
"Bản nháp tự động — chưa được giáo viên duyệt".

## Khác biệt so với các sản phẩm khác

Theo các bài báo và trang sản phẩm đội đã đọc (chưa dùng thử từng sản phẩm):

- **NotebookLM, Quizlet:** có bản đồ, câu hỏi, thẻ ghi nhớ, lưu tiến trình quiz hoặc học thích ứng trên nguồn của người học.
- **ChatGPT Study Mode, Gemini Guided Learning, Claude chế độ Học:** hỏi dẫn dắt, không đưa đáp án ngay.
- **ALEKS:** quyết định bằng mô hình tri thức, nhưng trên nội dung chuyên gia cố định, chủ yếu môn toán.

Từng tính năng riêng lẻ đều có ở nơi khác. Điểm của NodeTrail là **tổ hợp**, và mỗi điểm có mã làm bằng chứng:
quan hệ tiên quyết giữa các khái niệm, mức nắm vững riêng cho từng khái niệm, nội dung dựng ngay từ nguồn tin cậy kèm
trích dẫn bắt buộc, cổng kiểm chứng khác họ mô hình, và lý do quyết định đọc được. Đội **chưa có đánh giá đối chứng** cho
thấy cách này giúp học hiệu quả hơn.

## Kiến trúc kỹ thuật

- **Web** (`apps/web`): Next.js (App Router), TypeScript, Tailwind, React Flow + dagre cho bản đồ kiến thức; giao diện
  tiếng Việt mặc định, tiếng Anh phụ.
- **API** (`apps/api`): Python 3.12, FastAPI, Pydantic v2, uv.
- **Hàng đợi:** bảng `topic_jobs` trong Postgres (`SELECT … FOR UPDATE SKIP LOCKED`) cùng một worker riêng; tiến độ báo
  qua SSE có nhịp tim.
- **Dữ liệu:** Postgres + pgvector (`halfvec`, 1.024 chiều); migration trong `supabase/migrations/`.
- **Nhúng:** BAAI/bge-m3 qua máy chủ TEI chạy cục bộ, nên nội dung không gửi ra dịch vụ nhúng bên ngoài.
- **Cổng LLM** (`apps/api/app/llm`): mọi lời gọi mô hình đi qua một cổng; `routing.yaml` ánh xạ (hạng, tác vụ) tới danh
  sách nhà cung cấp có thứ tự; người kiểm luôn khác họ người tạo.
- **Quan sát:** log cấu trúc và Langfuse.

Hai chế độ: **Nhanh** (thư viện giáo trình mở đã lập chỉ mục và tệp người học tải lên) và **Nghiên cứu sâu**
(tác nhân tìm và đọc trong danh sách trang giáo dục mở được cho phép).

## Hiện trạng trung thực

| Hạng mục | Trạng thái |
|---|---|
| Bộ máy học tập (BKT, xếp trình độ, truy ngược gốc, FSRS, dấu vết) | Có mã và kiểm thử; 1.552 kiểm thử API và 50 kiểm thử web đạt trên nhánh tích hợp (đo cục bộ) |
| Thư viện giáo trình | 1.319 đoạn đã lập chỉ mục (Python, Logic, Thống kê) |
| Tải tệp PDF | Đã chạy thật một lần: 7 câu đã kiểm chứng và 3 gợi ý có trích dẫn trong 163 giây (có một lần thử lại) |
| Giao diện | Có bản đồ, bảng «Vì sao?» và luồng học; một số bước còn dùng dữ liệu mẫu, chưa nối hết với bộ máy thật |
| Nghiên cứu sâu | Có mã; chưa chứng minh chạy trọn vẹn trên nhánh chính |
| Độ chính xác xếp trình độ | Trên nhiễu mô phỏng chỉ đúng khoảng 56 đến 64% (mục tiêu 90%, chưa đạt) |
| Tỉ lệ bắt lỗi của cổng kiểm chứng | Chưa đo |
| Hiệu quả học | Chưa có dữ liệu |
| Chưa làm | Ghi chú thông minh, kế hoạch ôn thi, Elo cho độ khó câu hỏi, đăng nhập, câu hỏi có chấm mã |

Tham số BKT là giá trị khởi đầu theo tài liệu, chưa hiệu chỉnh trên dữ liệu người học thật.

## Dữ liệu và quyền riêng tư

Trong bản demo, tệp người dùng tải lên được đọc, cắt đoạn và gửi tới dịch vụ AI bên thứ ba (DeepSeek, Gemini). Việc này
chỉ dành cho demo cuộc thi, có thông báo hiển thị trước khi tải và cần người dùng chấp nhận; tệp và các đoạn sinh ra từ
tệp được xóa sau buổi trình bày. Trước khi dùng với người học thật cần rà soát quyền riêng tư. Giấy phép được ghi theo
từng nguồn; giấy phép "không phái sinh" bị loại. Bản Think Python dùng giấy phép phi thương mại.

## Chạy thử

Cần Docker, Python 3.12 với `uv`, Node.js với `pnpm`. Các hướng dẫn chi tiết (PowerShell, Windows):

- Cơ sở dữ liệu, API, migration: [`docker/LOCAL.md`](docker/LOCAL.md)
- Máy chủ nhúng bge-m3 (TEI): [`docker/TEI.md`](docker/TEI.md)
- Sao chép `.env.example` thành `.env` và tự điền khóa (không commit). Demo cần khóa cho DeepSeek và Gemini; các bước
  kiểm thử cục bộ không cần khóa nhà cung cấp.

Kiểm thử: `uv run pytest` trong `apps/api`; `pnpm test` trong `apps/web`.

## Bản đồ kho mã

| Đường dẫn | Nội dung |
|---|---|
| `apps/api/app/engine/` | Bộ máy học tập: `bkt.py`, `placement.py`, `graph.py`, `remediation.py`, `path.py`, `srs.py`, `trace.py` |
| `apps/api/app/rag/` | Cắt đoạn, nhúng, lập chỉ mục, truy xuất có trích dẫn, đánh giá truy xuất |
| `apps/api/app/llm/` | Cổng LLM và `routing.yaml` |
| `apps/api/app/schemas.py` | Các hợp đồng dữ liệu dùng chung |
| `apps/web/` | Ứng dụng web |
| `supabase/migrations/` | Cấu trúc cơ sở dữ liệu |
| `data/eval/` | Bộ câu hỏi tiếng Việt có nhãn để đo truy xuất |
| `specs/` | Đặc tả từng tính năng (Spec Kit) |
| `outputs/` | Kế hoạch diễn tập demo và bài giới thiệu |

Tài liệu của đội: [`SPEC.md`](SPEC.md) (sản phẩm làm gì), [`PLAN.md`](PLAN.md) (kế hoạch và hiện trạng),
[`TEAM.md`](TEAM.md) (phân vai 5 người, hợp đồng, tiến độ 24 giờ), [`MAP.md`](MAP.md) (vị trí các thành phần).

## Đội

Năm thành viên chia theo vai: P1 (trưởng nhóm, lõi học máy và bộ máy học tập), P2 (nền tảng, hạ tầng), P3 (cổng LLM,
nghiên cứu, truy xuất), P4 (nội dung, cổng kiểm chứng), P5 (giao diện, thiết kế Sena).
