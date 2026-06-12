# BẢNG PHÂN CHIA NHIỆM VỤ DỰ ÁN WEB PROXY SERVER

Dự án này gồm các chức năng cốt lõi của một hệ thống Web Proxy Server được phân bổ đồng đều cho 4 thành viên, tập trung vào lập trình Socket, phân tích giao thức HTTP/HTTPS và cấu hình các chính sách mạng cục bộ. Các phần giao diện quản trị web phụ trợ (Dashboard/Flask/HTML/CSS) được coi là công cụ bổ trợ và không nằm trong đánh giá phân chia nhiệm vụ chuyên môn mạng.

---

## 📊 BẢNG TỔNG HỢP PHÂN CHIA CÔNG VIỆC

| Thành viên | Trách nhiệm chính | File phụ trách chính |
| :--- | :--- | :--- |
| **Hào** | Nhân mạng HTTP & Giới hạn băng thông (Traffic Shaping) | `proxy.py` (Luồng HTTP & Throttling) |
| **Thưởng** | Kết nối HTTPS CONNECT & Giả lập sự cố máy chủ (Outage Simulation) | `proxy.py` (Luồng HTTPS Tunnel & Outage) |
| **An** | Bộ nhớ đệm (Smart Caching), Lọc Web Filter & Ghi Logs | `cache_manager.py`, `web_filter.py`, `logger.py` |
| **Quang Anh** | Giới hạn tần suất (Rate Limiting) & Xác thực cổng (Captive Portal) | `rate_limiter.py`, `proxy.py` (Phần Captive Portal) |

---

## 👤 HÀO: NHÂN MẠNG HTTP & GIỚI HẠN BĂNG THÔNG
* **Trọng tâm mạng:** Lập trình luồng socket TCP lắng nghe kết nối, bóc tách và phân tích tiêu đề bản tin HTTP thô, và kiểm soát tốc độ truyền tải gói tin ở tầng giao vận.

### 1. Mô tả chức năng
* **Proxy HTTP đa luồng:** Nhận HTTP Request từ client, phân tích tiêu đề thô, chuyển tiếp (forward) yêu cầu tới web server gốc và trả dữ liệu về trình duyệt.
* **Traffic Shaping (Giới hạn băng thông):** Điều phối tốc độ truyền dẫn gói tin qua TCP Socket (bytes/giây) giúp kiểm soát lưu lượng và băng thông mạng.

### 2. Các file & hàm phụ trách trong code
* **File phụ trách chính:** `proxy.py` (Phần lập trình mạng TCP/IP & HTTP)
* **Các hàm cụ thể:**
  * `main()`: Luồng chính khởi tạo server, liên kết socket lắng nghe cổng `8888`.
  * `shutdown_handler()`: Xử lý dừng hoạt động Proxy khi nhận tín hiệu kết thúc từ hệ điều hành.
  * `_inject_connection_close()`: Thay thế tiêu đề thành `Connection: close` để đóng socket TCP sau khi truyền xong bản tin.
  * `_recv_http_response()`: Nhận dữ liệu HTTP thông minh dựa vào trường `Content-Length`.
  * `send_throttled()`: Kiểm soát tốc độ truyền tải byte qua socket để giới hạn băng thông mạng (QoS).

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. Chạy Proxy Server: `python proxy.py`.
2. Cấu hình trình duyệt trỏ về Proxy `127.0.0.1:8888`.
3. **Demo HTTP Proxy:** Truy cập trang HTTP thông thường (ví dụ: `http://example.com`), chỉ ra trang web tải bình thường qua Proxy.
4. **Demo giới hạn băng thông:** Trong tệp cấu hình của Proxy, đặt giới hạn tốc độ truyền là **50 KB/s**. Thực hiện tải một file hoặc tải lại trang web bất kỳ để thấy trang web load chậm rõ rệt (giới hạn băng thông thành công).

---

## 👤 THƯỞNG: KẾT NỐI HTTPS CONNECT & GIẢ LẬP LỖI MÁY CHỦ GỐC

### 1. Mô tả chức năng
* **Đường hầm HTTPS Tunneling:** Xử lý phương thức `CONNECT` thiết lập đường truyền byte thô (tunnel) hai chiều phục vụ mã hóa SSL/TLS giữa client và web server bảo mật mà không giải mã dữ liệu (End-to-End Security).
* **Giả lập lỗi máy chủ gốc (Outage Simulation):** Giả lập trường hợp mạng/server web gốc bị ngắt kết nối (ngoại tuyến). Proxy sẽ bắt lỗi socket và phối hợp với Cache để tải trang offline.

### 2. Các file & hàm phụ trách trong code
* **File phụ trách chính:** `proxy.py` (Phần HTTPS Tunneling & Socket Outage)
* **Các hàm cụ thể:**
  * `handle_https_tunnel()`: Xử lý bắt tay CONNECT và chuyển tiếp byte thô hai chiều cho kết nối HTTPS qua các luồng phụ.
  * `connect_to_origin()`: Thiết lập kết nối TCP đến web server gốc, đồng thời ném lỗi giả lập ngắt kết nối khi tùy chọn ngoại tuyến được kích hoạt.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. Khởi động Proxy Server.
2. **Demo HTTPS CONNECT:** Mở trình duyệt truy cập một trang web mã hóa HTTPS (ví dụ: `https://google.com` hoặc `https://github.com`). Chỉ ra trang tải thành công và kiểm tra Terminal thấy in ra dòng log `🔒 TUNNEL`.
3. **Demo lỗi ngoại tuyến (Outage):** Kích hoạt chế độ ngoại tuyến trong tệp cấu hình. Mở trang web **chưa được cache** trước đó (ví dụ một domain lạ). Proxy sẽ chặn kết nối socket và hiển thị trang báo lỗi **502 Web Server Offline** tự thiết kế.

---

## 👤 AN: BỘ NHỚ ĐỆM (CACHE), WEB FILTER & GHI LOGS

### 1. Mô tả chức năng
* **Web Caching (RFC 7234):** Lưu trữ tạm thời các file tĩnh vào đĩa cứng của Proxy. Phân tích HTTP header điều khiển cache (`Cache-Control`, `ETag`...) để phản hồi nhanh, tiết kiệm băng thông đường truyền internet.
* **Tường lửa lọc tên miền & Chặn quảng cáo:** Đối chiếu tên miền trong danh sách cấm `blacklist.txt` và danh sách quảng cáo `adlist.txt` để chặn kết nối bằng mã **HTTP 403 Forbidden**.
* **Hệ thống Logger:** Ghi log kết nối mạng dạng JSON Lines đa luồng an toàn (Thread-safe) ra file để phục vụ theo dõi lưu lượng mạng.

### 2. Các file & hàm phụ trách trong code
* **Các file chính:**
  * `cache_manager.py` (Quản lý lưu trữ bộ nhớ đệm trên đĩa)
  * `web_filter.py` (Lọc tên miền blacklist/adlist)
  * `logger.py` (Ghi logs kết nối định dạng JSON)
* **Các hàm trong `proxy.py`:**
  * `handle_http_request()`: Luồng điều khiển kiểm tra cache, lưu cache mới khi tải tài nguyên HTTP.
  * `serve_offline_fallback()`: Phục vụ cache dự phòng (Offline Cache) và chèn banner cảnh báo khi server gốc gặp sự cố.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. **Demo Web Filter & Chặn quảng cáo:** Thêm một domain (ví dụ: `crazygames.com`) vào file `blacklist.txt`. Truy cập `http://crazygames.com` qua proxy, chỉ ra màn hình **403 Forbidden** chặn kết nối. Truy cập một trang web chứa quảng cáo trong `adlist.txt` để chỉ ra các request quảng cáo bị block.
2. **Demo Caching & Offline Fallback:** 
   * Truy cập trang HTTP `http://neverssl.com` lần đầu (Terminal báo `CACHE MISS`).
   * Tải lại trang lần 2 (Terminal báo `CACHE HIT` và có file lưu trong thư mục `cache/`).
   * Bật giả lập ngoại tuyến (Offline) trong tệp cấu hình, tải lại `http://neverssl.com`. Bạn sẽ thấy trang web vẫn tải được thành công (tải từ Offline Cache) kèm theo một banner màu vàng cam cảnh báo lỗi máy chủ gốc ở phía đầu trang.
3. **Demo Logger:** Mở file `logs/proxy.log` chỉ ra các logs định dạng JSON Lines được ghi lại đầy đủ thông tin: client IP, URL, status code, cache status.

---

## 👤 QUANG ANH: GIỚI HẠN TẦN SUẤT (RATE LIMIT) & XÁC THỰC CỔNG (CAPTIVE PORTAL)
* **Trọng tâm mạng:** Lập trình cơ chế lọc lưu lượng chống spam kết nối (Rate Limiting) và thiết kế hệ thống kiểm soát truy cập tầng ứng dụng (Captive Portal) thông qua cơ chế chuyển hướng HTTP (302 Redirect).

### 1. Mô tả chức năng
* **Rate Limiting (RFC 6585):** Sử dụng thuật toán Sliding Window đếm số yêu cầu từ IP. Chặn bằng mã **HTTP 429** đếm ngược tự reload nếu client gửi request quá nhanh để bảo vệ tài nguyên mạng.
* **Xác thực người dùng (Captive Portal):** Kiểm tra trạng thái IP của Client, chuyển hướng (HTTP 302 Redirect) các yêu cầu chưa xác thực sang trang đăng nhập cục bộ của Proxy và xử lý cấp quyền truy cập internet sau khi xác thực thành công.

### 2. Các file & hàm phụ trách trong code
* **Các file chính:**
  * `rate_limiter.py` (Quản lý giới hạn tần suất yêu cầu)
  * `proxy.py` (Phần xử lý cổng xác thực Captive Portal và chuyển hướng HTTP)
* **Các hàm trong `proxy.py`:**
  * `handle_client()`: Hàm trung tâm tiếp nhận Client, quản lý luồng kiểm tra Captive Portal Auth, Rate Limit và Filter.
  * `send_captive_portal_login()`, `send_captive_portal_success()`, `send_captive_portal_blocked()`: Các trang và logic phục vụ Captive Portal.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. **Demo Xác thực (Captive Portal):** 
   * Kích hoạt xác thực cổng đăng nhập trong tệp cấu hình Proxy.
   * Truy cập một trang HTTP bất kỳ (ví dụ `http://neverssl.com`). Proxy sẽ tự động hiển thị trang đăng nhập do nhóm thiết kế.
   * Nhập sai tài khoản $\rightarrow$ báo lỗi. Nhập đúng `admin` / `proxy123` $\rightarrow$ hiện màn hình Đăng nhập thành công và tự động chuyển hướng bạn quay lại trang web lúc đầu.
   * Cố tình vào trang HTTPS (như `https://google.com`) khi chưa đăng nhập $\rightarrow$ hiện trang 403 yêu cầu phải đăng nhập qua HTTP trước.
2. **Demo Rate Limit:** Cấu hình Rate Limit thành **10 request / 60 giây** trong tệp cấu hình. Mở trang HTTP: `http://neverssl.com` và nhấn `F5` reload liên tục 11 lần thật nhanh. Ở lần 11, trang màu cam **429 đếm ngược** sẽ xuất hiện.
