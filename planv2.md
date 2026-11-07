# planv2.md — P2: chạy project local và chuẩn bị tích hợp

## 1. Mục tiêu và hiện trạng

Chạy backend, database và embedding trên máy cá nhân. Đợt hiện tại chỉ thực hiện giai đoạn A–B trong phạm vi P2; giai đoạn C và demo tích hợp là công việc tiếp theo.

**Quyết định đã chốt với người dùng (2026-11-07):**

- Ưu tiên hoàn thành P2, chạy và nghiệm thu A–B trước; chưa triển khai C.
- Chỉ sửa các phần thuộc P2 theo `TEAM.md`; dùng code hiện có của các lane khác, không tự triển khai thay phần bàn giao còn thiếu.
- Máy cá nhân: RAM 32 GB, GTX 1060 VRAM 6 GB. Giữ phương án bge-m3 CPU cho mốc đầu; chưa cần cấu hình GPU. Đo thời gian và RAM khi ingest một chương.
- Người dùng hiện có DeepSeek API. A–B không cần gọi LLM hoặc dùng API key; gateway thuộc P3 và để sau.
- Chưa có nguồn sách và bộ câu hỏi bàn giao. Đề xuất dùng một chương Python cơ bản từ Think Python để nghiệm thu ingest; P3 cần chuẩn bị nguồn và giấy phép. Bộ câu hỏi/golden topic của P4 không phải điều kiện hoàn thành A–B.
- Chưa ấn định deadline; triển khai theo thứ tự A rồi B, ưu tiên P2.

**Đã có:** FastAPI với `/health`, Docker Postgres + pgvector, migration `0001–0002`, BKT/FSRS, pipeline ingest Think Python và CI.

**Chưa có:** frontend, API nghiệp vụ, database services, queue/worker, LLM gateway và dữ liệu sách trong repo.

Kế hoạch này bổ sung hướng chạy local; giữ `TEAM.md` làm nguồn chính thức cho quyền sở hữu và contracts. Không áp mốc giờ thi cho tiến độ local. Các checkbox là công việc cần thực hiện, chưa xác nhận đã hoàn thành.

## 2. Giai đoạn A — Chạy được backend hiện có

**P2 thực hiện theo thứ tự:**

- [x] Kiểm tra Docker Desktop chạy Linux containers, Python 3.12, Git và `uv`.
- [x] Hướng dẫn người dùng tự sao chép `.env.example` thành `.env`; không đọc hoặc ghi đè file secrets đã tồn tại.
- [x] Dùng database local: `postgresql://postgres:postgres@localhost:54322/nodetrail`.
- [x] Từ repo root, chạy `docker compose up -d db`; chờ database healthy.
- [x] Tại `apps/api`, cài dependencies, chạy migration và khởi động API:

  ```powershell
  uv sync --locked
  uv run python -m app.migrate
  uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ```

- [x] Xác nhận `http://localhost:8000/health` trả `status=ok`, `db=ok`; mở được `http://localhost:8000/docs`.
- [x] Viết hướng dẫn PowerShell cho khởi động, dừng, xem log và xử lý cổng bị chiếm. `docker compose down` giữ dữ liệu; thao tác xóa volume phải được ghi riêng là reset dữ liệu.

**Hoàn thành khi:** database và API khởi động được sau khi restart, migration chạy lại không tạo thay đổi, dữ liệu vẫn còn sau khi dừng container.

## 3. Giai đoạn B — Test và dữ liệu local

- [x] Giữ fixture tạo **database tạm mỗi lần chạy test** hiện có; chưa chuyển sang schema tạm vì Postgres local cho phép tạo database.
- [x] Chạy các kiểm tra sau tại `apps/api`:

  ```powershell
  uv run pytest -q
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy .
  ```

- [x] Ghi nhận riêng kết quả `mypy`. CI hiện đang coi lỗi mypy là thất bại, khác mô tả warn-only trong tài liệu; đồng bộ CI thành warn-only theo `TEAM.md`.
- [ ] **Phụ thuộc bàn giao, hiện chưa có:** P3 chuẩn bị một chương Think Python, kèm nguồn và giấy phép; P2 dùng pipeline của P1 để ingest. P2 vẫn thực hiện A và các kiểm tra không cần sách trong B trước.
- [ ] Khởi đầu bằng `BgeM3Embedder` CPU đang có: cài extra `embed`, tải model ở lần chạy đầu và ingest một chương trước khi mở rộng. Không bắt buộc GPU hoặc TEI cho mốc chạy local đầu tiên.
- [ ] Khi nguồn đã được P3 chuẩn bị tại `data/raw/thinkpython`, chạy tại `apps/api`:

  ```powershell
  uv sync --locked --extra embed
  uv run python -m app.rag.ingest ../../data/raw/thinkpython
  ```

- [ ] Kiểm tra ingest lại không nhân đôi chunks, vector đúng 1024 chiều và provenance được lưu.
- [ ] Khi tích hợp các lane, P2 review/merge migration theo thứ tự đã dành trong `TEAM.md`. Migration `0003` do P1 viết; đồng bộ code đọc/ghi vector với migration trước khi ingest toàn thư viện.

**Hoàn thành khi:** test dùng fake embedder chạy không cần tải model hoặc gọi LLM; ingest thật một chương thành công, dữ liệu dev không bị test tác động.

Nếu chưa nhận nguồn sách, ghi B là hoàn thành một phần và để mục ingest thật chưa đạt; không dùng kết quả fake embedder để thay thế nghiệm thu ingest thật.

## 4. Giai đoạn C — P2 xây nền tảng tích hợp (để sau A–B)

- [ ] Trước module/API mới, lập spec theo quy trình Spec Kit của repo; dùng contract do P1 cung cấp.
- [ ] Cung cấp API stubs theo contract để P5 phát triển giao diện; đánh dấu rõ dữ liệu fixture.
- [ ] Viết database services cho attempts, mastery, decision traces và review cards; engine của P1 tiếp tục độc lập database.
- [x] Viết migration `0006` cho `topic_jobs`, `llm_calls`; không sửa migration thuộc lane khác.
- [x] Xây queue Postgres và worker chạy bằng process riêng; claim job bằng `FOR UPDATE SKIP LOCKED`, ghi tiến trình và trạng thái lỗi.
- [x] Cung cấp trạng thái topic và SSE theo contract; heartbeat mỗi 15–20 giây, hỗ trợ client kết nối lại và tải trạng thái hiện tại.
- [x] Thêm cấu hình local cần thiết: CORS cho `http://localhost:3000`, API key dùng chung và địa chỉ API `http://localhost:8000`. Các biến hiện có trong `.env.example` chưa đồng nghĩa đã được code hỗ trợ.
- [x] Thêm log có `request_id`, `topic_id`, `tier`; Langfuse là tùy chọn local, thiếu credentials không chặn khởi động.

**Phụ thuộc tích hợp:**

| Thành viên | Phần cần bàn giao |
|---|---|
| P1 | Schemas/contracts, engine, retrieval, migration `0003–0004` |
| P3 | LLM gateway, route nghiệp vụ, nguồn sách và upload |
| P4 | Golden topic, graph, câu hỏi và tutor |
| P5 | Web local, gọi API và xử lý SSE reconnect |

LLM chỉ được gọi qua gateway của P3. DeepSeek là API người dùng hiện có, chưa xác nhận gateway hỗ trợ và chưa chọn model hoặc ngân sách. Khi triển khai tích hợp, P3/P1 chốt cấu hình theo contracts; chỉ có DeepSeek chưa đủ đáp ứng yêu cầu generator/verifier khác họ model. Các quyết định này không chặn A–B.

## 5. Nghiệm thu và giới hạn

**Đợt hiện tại — A–B:**

- [x] Máy mới có thể làm theo hướng dẫn để chạy DB, migrate, API và test.
- [x] Đạt điều kiện hoàn thành A: khởi động lại được, migration chạy lại an toàn và dữ liệu còn sau khi dừng container.
- [ ] Đạt điều kiện hoàn thành B: test cô lập dữ liệu dev, ghi nhận kết quả kiểm tra và ingest thật một chương không nhân đôi chunks, vector 1024 chiều, có provenance.
- [x] Checklist ghi rõ phần đã chạy thật, phần dùng fixture và phần đang chờ bàn giao.

**Nghiệm thu tương lai — C và tích hợp, không chặn đợt A–B:**

- [ ] Worker xử lý topic từ queued đến ready/failed; hai worker không nhận cùng một job.
- [ ] SSE có tiến trình, heartbeat và khôi phục được sau ngắt kết nối.
- [ ] Khi các lane bàn giao đủ: mở web local → chọn golden topic → placement → trả lời MCQ → lưu mastery/trace → xem trích dẫn.
- [ ] Lỗi database hoặc LLM có thông báo và log để truy tìm; không báo job thành công giả.

**Mặc định:** API/worker chạy trực tiếp bằng `uv`, chỉ database chạy Docker; embedding dùng CPU và cùng model bge-m3. Chưa yêu cầu Docker hóa toàn bộ ứng dụng.

**Hoãn khỏi đợt local:** cloud VM, AWS backup VM, Cloudflare Tunnel, GHCR/Watchtower và deploy Vercel. Upload, Deep Research và demo chủ đề bất kỳ là các mốc tiếp theo sau khi luồng golden topic chạy ổn.

## 6. Acceptance record - 2026-11-07

**A complete; B partially complete, awaiting P3's chapter handoff.**

- PowerShell runbook and detailed evidence: [docker/LOCAL.md](docker/LOCAL.md).
- Installed uv 0.13.7 and uv-managed Python 3.12.16; Docker Linux; Git 2.56.0.
- Database healthy. Migrations 0001-0002 applied, repeated safely, and survived Compose down/up.
- API restarted successfully: /health status=ok, db=ok; /docs HTTP 200.
- pytest: 133 passed, one TestClient/httpx dependency deprecation warning.
- Ruff lint/format passed; mypy passed on 25 files. CI mypy is now warning-only.
- Existing per-session temporary database fixture retained; dev chunk count stayed zero after tests.
- Instructions provided for user-managed .env copying. No secrets file read or created; default local DB used.
- data/raw/thinkpython is absent: embed extra/model download, real ingest, elapsed time, peak RAM and real vector/provenance acceptance remain pending. Fake embeddings do not satisfy this acceptance.
- Migration 0003 has not been handed off; no P1 vector changes available to review/merge.
- Phase C started on user instruction; see the record below.

## 7. Phase C implementation record - 2026-11-07

**P2 foundation implemented and tested; C remains partially complete pending lane handoffs.**
This supersedes the earlier decision to defer C. The missing book does not block platform work.

- Spec/plan/tasks written before code in `specs/p2-local/`; constitution in `.specify/memory/constitution.md`. Spec Kit CLI/commands are absent; manual artifacts do not imply CLI initialization is complete.
- P2 endpoints implemented from TEAM.md: POST /learners; GET /topics/cached; GET /topics/{id}; GET /topics/{id}/events. P1 schemas.py is still absent. Full P3 business stubs remain pending that schema handoff; no P3-owned files edited.
- Attempts/mastery/review persistence implemented with caller-owned transactions. Atomic rollback tested. Decision traces still await P1 migration 0004 and schema; the services checkbox remains incomplete.
- Migration 0006_platform.sql adds topic_jobs and llm_calls. Temporary test databases apply it successfully. Dev/shared DB application is deferred until 0003-0005 arrive and are reviewed in TEAM.md order.
- Queue claims use FOR UPDATE SKIP LOCKED; independent worker process supports explicit fixtures, persists missing-P3 failures, and does not mark real jobs ready. Concurrent claim test passed.
- Topic GET and SSE share a durable snapshot. SSE polls changes, emits heartbeat every 15 seconds and sends current state on reconnect. Heartbeat/progress/reconnect tested. No historical event replay is promised.
- Local CORS and optional X-API-Key are supported; request IDs and structured JSON logs added using standard logging. Langfuse is not initialized, so missing credentials cannot block startup; gateway telemetry still awaits P3.
- Verification: 137 tests passed; ruff lint and format passed; mypy passed on 32 files. Existing dependency warning: TestClient/httpx deprecation. Web checks skipped because apps/web is absent.
- Operational instructions and limits: docker/LOCAL.md. Crash-after-claim recovery is manual until P3 provides an idempotent pipeline contract. Real processing, actual LLM failures and full web integration have not been exercised.
- B real ingest remains pending P3's licensed chapter. No real model/LLM requests, new dependencies, commits or pushes.
