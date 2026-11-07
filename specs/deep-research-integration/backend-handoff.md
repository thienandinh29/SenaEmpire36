# Bàn giao sửa luồng research và phát hành bài học

Mục tiêu rộng hoặc nguồn không phù hợp từng tạo graph trước khi có đủ câu hỏi
đạt kiểm chứng. Một số lỗi trích dẫn và thay đổi dữ liệu dùng chung còn làm mất
hiệu lực câu hỏi đã kiểm chứng. Commit này sửa backend và test, không bao gồm UI
thử nghiệm hay log/credential local.

## Luồng và điều kiện phát hành

Mục tiêu → lập truy vấn → tìm/đọc nguồn → kiểm tra giấy phép và nội dung giảng dạy
→ lưu/embedding → lấy context → graph nháp → sinh/kiểm chứng câu hỏi cho từng
khái niệm → lưu và kiểm tra lại → phát hành → người học xem/xác nhận → học.

- Graph nháp được lưu làm checkpoint; `graph_ready=false` cho tới khi các câu hỏi
  đủ điều kiện và đã được lưu. Lỗi kiểm chứng không phát hành graph nháp.
- API xem graph, review, confirm và bắt đầu học chặn topic chưa có trạng thái
  `ready` cùng cả hai cờ `graph_ready`/`items_ready`. Không cần migration mới.
- Worker `--pipeline` giới hạn bài đầu ở 3 khái niệm và 6 đoạn context. Graph giữ
  quan hệ tiên quyết hợp lệ; checkpoint cũng phải tuân thủ giới hạn/context mới.
- Số câu hỏi đạt kiểm chứng tối thiểu là 6 và phải phủ mọi khái niệm. Lỗi coverage
  nêu rõ tên khái niệm, không quy mọi thất bại thành thiếu tài liệu.

## Sửa các điểm tích hợp

- Quick chọn thư viện theo mục tiêu thay vì ghim mặc định Python.
- Deep hỗ trợ Brave và Tavily; Tavily dùng basic search, không tự nâng độ sâu.
  Truy vấn được chuẩn hóa từ mục tiêu, gồm tiếng Việt không dấu. Các biến thể dùng
  chung ngân sách tối đa 15 search/12 lượt đọc và deadline Deep hiện hữu.
- Chỉ xếp hạng URL được nhà cung cấp trả về. Đọc trang thật, kiểm tra giấy phép và
  yêu cầu chọn đoạn giảng dạy thực sự liên quan trước khi chọn nguồn.
- Nguồn web mới và upload được lưu/embedding trong đúng topic. Nội dung đổi làm
  vector cũ mất hiệu lực; retry giữ các batch embedding đã hoàn tất.
- Chunk prompt có ánh xạ source ID rõ ràng. Câu hỏi giữ provenance và dùng model
  family độc lập để kiểm chứng; không truyền đáp án chuẩn vào request verifier.
- Mô tả misconception dùng chung được cố định trước kiểm chứng; lưu câu mới không
  ghi đè mô tả khiến hash của câu cũ thay đổi.
- Trích dẫn sai định dạng được sửa tối đa một lần trong deadline kiểm chứng cũ,
  chỉ khi verdict độc lập đã đạt các điều kiện khác. Vẫn cần quote khớp nguồn thật;
  không retry câu trả lời sai, lỗi provider hoặc verdict không an toàn.
- Công cụ import checkpoint chỉ ghi câu còn hợp lệ theo hash, mặc định dry-run và
  CLI chỉ cho phép PostgreSQL local.

## Cấu hình và kiểm tra

Điền credential vào `.env` local từ `.env.example`; không đưa vào Git. Với Tavily:
`SEARCH_PROVIDER=tavily`, `SEARCH_API_KEY=<key local>`. Cấu hình database, TEI và
model generation/verification có model family độc lập trước khi chạy worker.

Từ `apps/api`, dùng môi trường Python đã cài dependency của dự án:

```powershell
python -m app.research.search          # chỉ kiểm tra cấu hình, không gọi mạng
python -m app.research.search --live   # một truy vấn search thật
python -m app.jobs.worker --pipeline
```

Các lệnh CI: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest -q`.
Kiểm tra local: **1.489 test pass**, Ruff/format và mypy toàn bộ API/test pass.
Test PostgreSQL dùng database tạm riêng; có kiểm tra graph nháp/failed bị chặn
ở cả review, confirm, graph và placement, cùng luồng published → học thành công.

Các lượt smoke local đã chạy research thật cho xác suất, sinh học và ngữ pháp
tiếng Anh, gồm DB/RAG, xác nhận graph, placement, luyện tập và hint. Đây là kiểm
tra tích hợp bằng người học giả lập; chưa phải kiểm chứng hiệu quả giáo dục hay
độ ổn định cho mọi mục tiêu. Không tuyên bố production GO hoặc tiết kiệm token
định lượng từ các kết quả này. Log và receipt local không nằm trong commit.

## Sửa luồng tài liệu toán và truy xuất

Lượt kiểm tra “học đạo hàm” phát hiện lỗi ở backend, trước khi frontend có thể
hiển thị bài học: trang tải PDF bị coi như nội dung, trích dẫn công thức bị model
chép lại sai định dạng, rồi truy vấn RAG tiếng Việt chọn macro TeX và khung giao diện
trong tài liệu tiếng Anh. Có nguồn tìm được nhưng không có ngữ cảnh tốt để sinh bài.

- Bộ xếp hạng xét tối đa 24 ứng viên từ hai truy vấn thay vì cắt mỗi nhóm còn sáu;
  vẫn chỉ đọc tối đa 12 nguồn và chỉ chấp nhận URL đã được search trả về.
- MIT dùng cụm chủ đề ngắn để tìm trang chương. Reader chỉ theo liên kết PDF thực
  sự xuất hiện trên trang resource, đúng khóa học và tệp. Trang và PDF đều tính vào
  ngân sách đọc; giữ kiểm tra SSRF, giấy phép, hạn chế AI và hạn chế trong chính tệp.
- Nếu search trả về mục lục MIT, reader lấy tối đa 12 liên kết chương thực trong
  cùng khóa học rồi xếp hạng theo mục tiêu; không coi mục lục là bài học và không
  truyền giấy phép của mục lục thay cho giấy phép trang chương/tệp.
- Giấy phép của trang resource được giữ cùng URL provenance; chunk PDF giữ số trang
  và văn bản của từng trang, không lặp toàn bộ tệp cho mỗi trang.
- Kiểm tra liên quan chọn ID đoạn văn do server cấp, tránh chép lại công thức.
  Việc kiểm chứng đáp án vẫn dùng model family độc lập và kiểm tra bằng chứng cũ.
- Reader lấy phần bài học LibreTexts cho indexing; văn bản HTML đầy đủ vẫn được
  kiểm tra riêng về giấy phép. Truy vấn research chuẩn hóa được truyền tiếp vào RAG,
  còn mục tiêu gốc của người học vẫn được dùng để kiểm tra phạm vi bản đồ.
- RAG của job chỉ tìm trong chunk hiện tại. Tài liệu cũ còn lưu sau retry không được
  trộn vào ngữ cảnh mới; SQL loại cả vector null. Lỗi bất ngờ ghi stage, loại exception
  và vị trí hàm/dòng, không ghi nội dung exception hay khóa. Lỗi bước câu hỏi được
  báo riêng thay vì gộp thành “không thể xây lộ trình”.

Test hồi quy bao gồm PDF thực được liên kết, ngân sách đọc, giấy phép ND và quyền
trong tệp, provenance từng trang, công thức toán, loại bỏ UI/macro, ứng viên ở cuối
hai trang search và truy vấn chuẩn hóa đi tới retriever. Test tích hợp vẫn kiểm tra
Deep → SQL → xác nhận bản đồ → placement → practice bằng người học giả lập.

Sau các sửa đổi này: toàn bộ **1.508 test pass**, Ruff check/format và mypy pass.
Một lượt sinh câu hỏi thật đã tạo sáu câu được kiểm chứng trên checkpoint đạo hàm;
đây chưa đủ để kết luận cả luồng research ổn định. Lượt sinh trước đó lỗi bất ngờ
không giữ nguyên nhân gốc; log theo stage được bổ sung để chẩn đoán lần tiếp theo.
