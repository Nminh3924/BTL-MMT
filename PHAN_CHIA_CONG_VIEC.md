# BẢNG PHÂN CHIA NHIỆM VỤ DỰ ÁN WEB PROXY SERVER (TỐI ƯU ĐỀU ĐỘ KHÓ 16-18)

Dự án này gồm **10 chức năng** được phân bổ cực kỳ đồng đều cho **4 thành viên** với tổng điểm độ khó của mỗi người dao động từ **16 đến 18 điểm** (khoảng chênh lệch cực kỳ nhỏ, bảo đảm công bằng tuyệt đối).

---

## 📊 BẢNG TỔNG HỢP PHÂN CHIA CÔNG VIỆC

| Thành viên | Trách nhiệm chính | Tổng độ khó | File phụ trách chính |
| :--- | :--- | :--- | :--- |
| **Thành viên 1** | Nhân mạng HTTP & Giới hạn băng thông | **16 / 20** | `proxy.py` (Phần HTTP & Throttling) |
| **Thành viên 2** | Kết nối HTTPS CONNECT & Giả lập lỗi máy chủ gốc | **16 / 20** | `proxy.py` (Phần HTTPS Tunnel & Outage) |
| **Thành viên 3** | Bộ nhớ đệm (Cache), Lọc Web Filter & Ghi Logs | **18 / 20** | `cache_manager.py`, `web_filter.py`, `logger.py` |
| **Thành viên 4** | Chống DDoS (Rate Limit), Xác thực Proxy (Captive Portal) & Dashboard | **16.5 / 20** | `rate_limiter.py`, `dashboard.py`, `templates/` |

---

## 👤 THÀNH VIÊN 1: NHÂN MẠNG HTTP & GIỚI HẠN BĂNG THÔNG
* **Tổng điểm độ khó:** **`16 / 20`** (Gồm: Chức năng 1 - 10 điểm, Chức năng 7 - 6 điểm).

### 1. Mô tả chức năng
* **Proxy HTTP đa luồng:** Nhận HTTP Request từ client, phân tích tiêu đề thô, chuyển tiếp (forward) yêu cầu tới web server gốc và trả dữ liệu về trình duyệt.
* **Traffic Shaping (Giới hạn băng thông):** Điều phối tốc độ truyền dẫn gói tin qua TCP Socket (bytes/giây) giúp kiểm soát lưu lượng và băng thông mạng.

### 2. Các file & hàm phụ trách trong code
* **File phụ trách:** [proxy.py](file:///d:/MMT/proxy.py) (Phần Core & HTTP)
* **Các hàm cụ thể:**
  * `main()`: Luồng chính khởi tạo server, liên kết socket lắng nghe cổng `8888`.
  * `shutdown_handler()`: Xử lý dừng hoạt động Proxy khi nhấn `Ctrl+C`.
  * `_inject_connection_close()`: Thay thế header thành `Connection: close` để đóng kết nối TCP sau khi gửi xong.
  * `_recv_http_response()`: Nhận dữ liệu HTTP thông minh dựa vào trường `Content-Length`.
  * `send_throttled()`: Kiểm soát tốc độ truyền tải byte qua socket để giới hạn băng thông.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. Chạy Proxy Server: `python proxy.py`.
2. Cấu hình trình duyệt trỏ về Proxy `127.0.0.1:8888`.
3. **Demo HTTP Proxy:** Truy cập trang HTTP thông thường (ví dụ: `http://example.com`), chỉ ra trang web tải bình thường qua Proxy.
4. **Demo giới hạn băng thông:** Trên giao diện Dashboard, đặt giới hạn tốc độ truyền là **50 KB/s**. Thực hiện tải một file hoặc tải lại trang web bất kỳ để thấy trang web load chậm rõ rệt (giới hạn băng thông thành công).

---

## 👤 THÀNH VIÊN 2: KẾT NỐI HTTPS CONNECT & GIẢ LẬP LỖI MÁY CHỦ GỐC
* **Tổng điểm độ khó:** **`16 / 20`** (Gồm: Chức năng 2 - 9 điểm, Chức năng 8 - 7 điểm).

### 1. Mô tả chức năng
* **Đường hầm HTTPS Tunneling:** Xử lý phương thức `CONNECT` thiết lập đường truyền byte thô (tunnel) hai chiều phục vụ mã hóa SSL/TLS giữa client và web server bảo mật.
* **Giả lập lỗi máy chủ gốc (Outage Simulation):** Giả lập trường hợp server web gốc bị sập/bảo trì (ngoại tuyến). Proxy sẽ bắt lỗi này và phối hợp với Cache để tải trang offline.

### 2. Các file & hàm phụ trách trong code
* **File phụ trách:** [proxy.py](file:///d:/MMT/proxy.py) (Phần HTTPS & Server Connection Outage)
* **Các hàm cụ thể:**
  * `handle_https_tunnel()`: Xử lý bắt tay CONNECT và chuyển tiếp byte thô hai chiều cho kết nối HTTPS.
  * `connect_to_origin()`: Kết nối đến web server gốc, đồng thời ném lỗi giả lập khi nút bật lỗi được kích hoạt.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. Khởi động Proxy Server.
2. **Demo HTTPS CONNECT:** Mở trình duyệt truy cập một trang web mã hóa HTTPS (ví dụ: `https://google.com` hoặc `https://github.com`). Chỉ ra trang tải thành công và kiểm tra Terminal thấy in ra dòng log `🔒 TUNNEL`.
3. **Demo lỗi ngoại tuyến (Outage):** Kích hoạt *"Giả Lập Ngoại Tuyến (Offline)"* trên Dashboard. Mở trang web **chưa được cache** trước đó (ví dụ một domain lạ). Proxy sẽ chặn kết nối và hiển thị trang báo lỗi **502 Web Server Offline** tự thiết kế màu đỏ cực kỳ trực quan.

---

## 👤 THÀNH VIÊN 3: BỘ NHỚ ĐỆM (CACHE), WEB FILTER & GHI LOGS
* **Tổng điểm độ khó:** **`18 / 20`** (Gồm: Chức năng 3 - 8 điểm, Chức năng 4 - 5.5 điểm, Chức năng 9 - 4.5 điểm).

### 1. Mô tả chức năng
* **Web Caching (RFC 7234):** Lưu trữ tạm thời các file tĩnh vào đĩa cứng của Proxy. Phân tích HTTP header điều khiển cache (`Cache-Control`, `ETag`...) để phản hồi nhanh.
* **Tường lửa lọc tên miền & Chặn quảng cáo:** Đối chiếu tên miền trong blacklist/adlist và chặn bằng mã **HTTP 403 Forbidden**.
* **Hệ thống Logger:** Ghi log JSON Lines đa luồng an toàn (Thread-safe) ra file và tổng hợp số liệu thống kê.

### 2. Các file & hàm phụ trách trong code
* **Các file chính:**
  * [cache_manager.py](file:///d:/MMT/cache_manager.py) *(Toàn bộ file Caching)*
  * [web_filter.py](file:///d:/MMT/web_filter.py) *(Toàn bộ file Web Filter)*
  * [logger.py](file:///d:/MMT/logger.py) *(Toàn bộ file Logger)*
* **Các hàm trong [proxy.py](file:///d:/MMT/proxy.py):**
  * `handle_http_request()`: Luồng điều khiển kiểm tra cache, lưu cache mới khi tải file.
  * `serve_offline_fallback()`: Phục vụ cache dự phòng (Offline Cache) và chèn banner cảnh báo khi server gốc bị sập.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. **Demo Web Filter:** Thêm một domain bất kỳ (ví dụ: `epicgames.com`) vào file `blacklist.txt`. Truy cập `http://epicgames.com` qua proxy, chỉ ra màn hình **403 Forbidden** màu đỏ chặn kết nối.
2. **Demo Caching & Offline Fallback:** 
   * Truy cập trang HTTP `http://example.com` lần đầu (Dashboard báo `🌐 CACHE MISS`).
   * Tải lại trang lần 2 (Dashboard báo `💾 CACHE HIT` và có file lưu trong thư mục `cache/`).
   * Bật giả lập ngoại tuyến (Offline) trên Dashboard, tải lại `http://example.com`. Bạn sẽ thấy trang web vẫn tải được thành công (tải từ Offline Cache) kèm theo một **banner màu vàng cam cảnh báo lỗi máy chủ gốc** ở phía đầu trang!
3. **Demo Logger:** Mở file [logs/proxy.log](file:///d:/MMT/logs/proxy.log) chỉ ra các logs định dạng JSON Lines được ghi lại đầy đủ.

---

## 👤 THÀNH VIÊN 4: CHỐNG DDOS (RATE LIMIT), XÁC THỰC PROXY & DASHBOARD
* **Tổng điểm độ khó:** **`16.5 / 20`** (Gồm: Chức năng 5 - 7.5 điểm, Chức năng 6 - 5 điểm, Chức năng 10 - 4 điểm).

### 1. Mô tả chức năng
* **Rate Limiting (RFC 6585):** Sử dụng thuật toán Sliding Window đếm số yêu cầu từ IP. Chặn bằng mã **HTTP 429** đếm ngược tự reload nếu truy cập quá nhanh.
* **Xác thực người dùng (Captive Portal):** Khi chưa đăng nhập, tự động chuyển hướng và chặn mọi yêu cầu để hiện một **Trang đăng nhập tự thiết kế độc lập** bắt nhập tài khoản trước khi cấp quyền truy cập Internet.
* **Giao diện Dashboard Flask:** Máy chủ web giám sát lưu lượng và điều khiển bật/tắt các thông số.

### 2. Các file & hàm phụ trách trong code
* **Các file chính:**
  * [rate_limiter.py](file:///d:/MMT/rate_limiter.py) *(Toàn bộ file Rate Limit)*
  * [dashboard.py](file:///d:/MMT/dashboard.py) *(Toàn bộ file Flask Server)*
  * [templates/rate_limited.html](file:///d:/MMT/templates/rate_limited.html) và [templates/dashboard.html](file:///d:/MMT/templates/dashboard.html)
* **Các hàm trong [proxy.py](file:///d:/MMT/proxy.py):**
  * `handle_client()`: Hàm trung tâm tiếp nhận Client, quản lý luồng kiểm tra Captive Portal Auth, Rate Limit và Filter.
  * `send_captive_portal_login()`, `send_captive_portal_success()`, `send_captive_portal_blocked()`: Các trang và logic phục vụ Captive Portal.
  * `start_dashboard()`: Chạy luồng phụ cho Flask.

### 3. Hướng dẫn chạy và Demo (Thuyết trình)
1. **Demo Dashboard:** Truy cập `http://localhost:5000` chỉ ra Dashboard thống kê đang cập nhật log trực tiếp.
2. **Demo Xác thực (Captive Portal):** 
   * Bật toggle *"Bật Xác Thực Đăng Nhập"* trên Dashboard.
   * Truy cập một trang HTTP bất kỳ (ví dụ `http://neverssl.com`). Proxy sẽ tự động hiển thị **trang đăng nhập bảo mật màu tím/tối** do bạn tự thiết kế.
   * Nhập sai tài khoản $\rightarrow$ báo lỗi đỏ. Nhập đúng `admin` / `proxy123` $\rightarrow$ hiện màn hình Đăng nhập thành công và tự động chuyển hướng bạn quay lại trang web lúc đầu.
   * Cố tình vào trang HTTPS (như `https://google.com`) khi chưa đăng nhập $\rightarrow$ hiện trang 403 yêu cầu phải đăng nhập qua HTTP trước.
3. **Demo Rate Limit:** Cấu hình Rate Limit thành **10 request / 60 giây**. Mở trang HTTP: **`http://neverssl.com`** và nhấn `F5` reload liên tục 11 lần thật nhanh. Ở lần 11, trang màu cam **429 đếm ngược** sẽ xuất hiện.
