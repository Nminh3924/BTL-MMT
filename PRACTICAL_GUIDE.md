# Ứng Dụng Thực Tế & Hướng Dẫn Công Cụ Triển Khai

Tài liệu này giải thích một cách **dễ hiểu nhất** về việc đề tài **Custom Web Proxy Server với Caching & Web Filter** có thể ứng dụng vào những bài toán thực tế nào trong đời sống, và bạn cần chuẩn bị những công cụ, ngôn ngữ lập trình gì để có thể xây dựng và demo thành công.

---

## 📖 Phần 1: Proxy Server Là Gì? (Giải Thích Đơn Giản)

Hãy tưởng tượng bạn đang ngồi ở quán cà phê và muốn gọi một ly nước. Thay vì bạn tự đi vào bếp lấy nước (kết nối trực tiếp đến Web Server), bạn gọi **người phục vụ** (Proxy Server) để nhờ họ mang nước cho bạn.

Người phục vụ này có thể:
* **Mang nước cho bạn** — chuyển tiếp yêu cầu của bạn đến bếp và mang kết quả về (Proxy cơ bản).
* **Nhớ món bạn hay gọi** — lần sau bạn gọi lại món cũ, họ mang ra ngay mà không cần vào bếp lại (Caching).
* **Từ chối phục vụ một số món** — nếu quán cấm bán rượu cho người dưới tuổi, người phục vụ sẽ từ chối (Web Filtering).
* **Ghi lại tất cả đơn hàng** — quản lý quán có thể xem ai đã gọi gì, lúc mấy giờ (Logging & Dashboard).

Đó chính xác là cách **Proxy Server** hoạt động trong thế giới mạng máy tính.

---

## 🌍 Phần 2: Ứng Dụng Thực Tế Của Đề Tài

### Ứng dụng 1: Tăng tốc Internet cho văn phòng / trường học

**Bài toán thực tế:**
Một văn phòng có 50 nhân viên, tất cả cùng truy cập các trang web giống nhau mỗi ngày (báo VnExpress, Gmail, trang nội bộ công ty...). Mỗi lần mở trang, trình duyệt của từng người đều phải tải lại toàn bộ hình ảnh, file CSS, JavaScript từ Internet. Điều này gây lãng phí băng thông rất lớn.

**Proxy Server giải quyết như thế nào:**
* Khi nhân viên đầu tiên truy cập VnExpress, Proxy tải trang từ Internet và **lưu một bản sao** (cache) vào ổ cứng cục bộ.
* Khi 49 nhân viên còn lại truy cập cùng trang đó, Proxy **trả về bản sao từ ổ cứng** mà không cần tải lại từ Internet.
* **Kết quả:** Tốc độ tải trang nhanh hơn gấp nhiều lần. Tiết kiệm băng thông Internet cho cả văn phòng.

---

### Ứng dụng 2: Kiểm soát truy cập mạng (Parental Control / Quản lý nhân viên)

**Bài toán thực tế:**
* Phụ huynh muốn chặn con cái truy cập các trang web không phù hợp (web đen, game online...).
* Công ty muốn ngăn nhân viên lướt mạng xã hội (Facebook, TikTok, YouTube) trong giờ làm việc.

**Proxy Server giải quyết như thế nào:**
* Cấu hình một danh sách đen (Blacklist) chứa các tên miền bị cấm: `facebook.com`, `tiktok.com`, `youtube.com`...
* Khi người dùng cố truy cập các trang này, Proxy **chặn ngay lập tức** và hiển thị một trang thông báo: *"Trang web này đã bị chặn bởi hệ thống quản trị mạng"*.
* Người dùng không thể vượt qua nếu tất cả traffic đều buộc phải đi qua Proxy.

---

### Ứng dụng 3: Chặn quảng cáo trên toàn mạng nội bộ (Network-level Ad Blocker)

**Bài toán thực tế:**
Quảng cáo trên các trang web không chỉ gây khó chịu mà còn tiêu tốn băng thông mạng. Mỗi trang web có thể tải thêm 20-30 request quảng cáo từ các server bên thứ ba (Google Ads, Facebook Pixel, các mạng quảng cáo...).

**Proxy Server giải quyết như thế nào:**
* Proxy duy trì một danh sách các host quảng cáo phổ biến (ví dụ: `ads.google.com`, `doubleclick.net`, `facebook.net/tr`...).
* Khi trình duyệt cố tải nội dung quảng cáo từ các host này, Proxy **chặn request ngay** mà không chuyển tiếp đến Internet.
* **Kết quả:** Trang web tải nhanh hơn, sạch sẽ hơn, và tiết kiệm dung lượng mạng cho toàn bộ thiết bị trong mạng LAN mà không cần cài extension AdBlock trên từng máy.

---

### Ứng dụng 4: Giám sát và phân tích lưu lượng mạng (Network Monitoring)

**Bài toán thực tế:**
Quản trị viên mạng của một trường học cần biết: sinh viên đang truy cập những trang web nào? Ai dùng nhiều băng thông nhất? Có ai đang tải file lớn bất thường không?

**Proxy Server giải quyết như thế nào:**
* Mọi request HTTP đi qua Proxy đều được **ghi lại nhật ký** (log): thời gian, địa chỉ IP nguồn, URL truy cập, dung lượng dữ liệu tải về.
* Dashboard trực quan hiển thị:
  * Top 10 trang web được truy cập nhiều nhất.
  * Tổng lưu lượng mạng theo giờ/ngày.
  * Tỷ lệ dữ liệu được phục vụ từ Cache (Cache Hit) so với dữ liệu phải tải từ Internet (Cache Miss).
* Quản trị viên có cái nhìn tổng quan về hành vi sử dụng mạng của toàn bộ hệ thống.

---

### Ứng dụng 5: Công cụ học tập và nghiên cứu giao thức mạng

**Bài toán thực tế:**
Sinh viên học môn Mạng Máy Tính cần hiểu cách giao thức HTTP/HTTPS hoạt động thực tế, nhưng chỉ đọc lý thuyết thì rất khó hình dung.

**Proxy Server giải quyết như thế nào:**
* Khi chạy Proxy, bạn có thể **nhìn thấy trực tiếp** từng gói tin HTTP đi qua trên Terminal:
  * Dòng Request Line: `GET /index.html HTTP/1.1`
  * Các Header: `Host: example.com`, `User-Agent: Chrome/120`, `Accept-Encoding: gzip`...
  * Status Code phản hồi: `200 OK`, `304 Not Modified`, `403 Forbidden`...
* Đây là cách học **"learning by doing"** — bạn tự tay xây dựng một phần của hạ tầng Internet mà hàng ngày vẫn đang sử dụng.

---

## 🛠️ Phần 3: Công Cụ & Ngôn Ngữ Cần Chuẩn Bị

### A. Ngôn ngữ lập trình: Python 3

| Tiêu chí | Chi tiết |
|---|---|
| **Phiên bản** | Python 3.8 trở lên |
| **Lý do chọn** | Thư viện socket tích hợp sẵn, cú pháp ngắn gọn dễ đọc, cộng đồng hỗ trợ lớn |
| **Kiểm tra đã cài chưa** | Mở Command Prompt (CMD) hoặc PowerShell, gõ: `python --version` |
| **Cài đặt (nếu chưa có)** | Tải bản cài đặt tại [python.org/downloads](https://www.python.org/downloads/). **Quan trọng:** Khi cài đặt, nhớ tích chọn ✅ **"Add Python to PATH"** ở bước đầu tiên |

**Các module Python sử dụng (tất cả đều có sẵn, không cần cài thêm):**

| Module | Vai trò trong dự án |
|---|---|
| `socket` | Tạo kết nối TCP, lắng nghe và chuyển tiếp gói tin thô |
| `threading` | Xử lý đa luồng — mỗi kết nối từ trình duyệt chạy trên một luồng riêng |
| `hashlib` | Băm URL thành tên file để lưu cache trên ổ đĩa (dùng MD5 hoặc SHA-256) |
| `os`, `time` | Quản lý file cache trên đĩa, kiểm tra thời gian hết hạn (TTL) |
| `json` | Lưu trữ metadata của cache (thời gian tạo, headers gốc, kích thước...) |

**Module bổ sung (cài qua pip, dùng cho Dashboard nâng cao):**

| Module | Cài đặt | Vai trò |
|---|---|---|
| `flask` | Mở CMD, gõ: `pip install flask` | Tạo web server nhỏ phục vụ trang Dashboard giám sát |

---

### B. Trình soạn thảo mã nguồn (IDE)

**Khuyến nghị: Visual Studio Code (VS Code)**

* Miễn phí, nhẹ, chạy trên mọi hệ điều hành.
* Các Extension nên cài:
  * **Python** — Gợi ý code, debug, chạy trực tiếp.
  * **Markdown Preview Mermaid Support** — Xem sơ đồ kiến trúc trong file README.

---

### C. Công cụ kiểm thử & Debug mạng

#### 1. Trình duyệt Firefox (Quan trọng nhất cho Demo)

**Tại sao dùng Firefox mà không phải Chrome?**
* Firefox cho phép cấu hình Proxy **riêng biệt bên trong trình duyệt**, không ảnh hưởng đến kết nối mạng của toàn bộ hệ điều hành.
* Chrome/Edge thì bắt buộc phải thay đổi cài đặt Proxy của cả hệ thống — khi Proxy của bạn bị lỗi hoặc tắt, toàn bộ máy tính sẽ mất mạng.

**Cách cấu hình Firefox đi qua Proxy:**
1. Mở Firefox → Gõ vào thanh địa chỉ: `about:preferences`
2. Kéo xuống cuối trang → Mục **Network Settings** → Nhấn **Settings...**
3. Chọn **Manual proxy configuration**
4. Nhập:
   * HTTP Proxy: `127.0.0.1` — Port: `8888`
   * Tích chọn ✅ **Also use this proxy for HTTPS**
5. Nhấn **OK**

Từ lúc này, tất cả traffic của Firefox sẽ đi qua chương trình Proxy của bạn.

---

#### 2. cURL (Công cụ dòng lệnh gửi HTTP Request)

**cURL là gì?**
Một chương trình chạy trên CMD/PowerShell cho phép bạn gửi HTTP Request thủ công và xem chi tiết toàn bộ quá trình gửi/nhận gói tin. Rất hữu ích để test Proxy mà không cần mở trình duyệt.

**Tin tốt:** Windows 10/11 **đã tích hợp sẵn cURL**, bạn không cần cài thêm gì cả.

**Kiểm tra bằng cách mở CMD hoặc PowerShell, gõ:**
```cmd
curl --version
```

**Các lệnh test Proxy thường dùng (chạy trong CMD):**
```cmd
:: Test 1: Gửi request HTTP qua Proxy — xem Proxy có chuyển tiếp đúng không
curl -x http://127.0.0.1:8888 http://example.com -v

:: Test 2: Gửi request HTTPS qua Proxy — xem HTTPS Tunneling có hoạt động không
curl -x http://127.0.0.1:8888 https://www.google.com -v

:: Test 3: Gửi request đến trang bị chặn — xem Web Filter có trả về 403 không
curl -x http://127.0.0.1:8888 http://facebook.com -v

:: Test 4: Gửi cùng 1 request 2 lần — lần 2 phải nhanh hơn rõ rệt nhờ Cache
curl -x http://127.0.0.1:8888 http://example.com -o NUL -w "Thoi gian tai: %%{time_total}s"
curl -x http://127.0.0.1:8888 http://example.com -o NUL -w "Thoi gian tai: %%{time_total}s"
```

Tham số `-v` (verbose) sẽ in ra toàn bộ header HTTP gửi đi và nhận về, giúp bạn đối chiếu trực tiếp với lý thuyết về cấu trúc gói tin HTTP.

---

#### 3. Wireshark (Công cụ bắt và phân tích gói tin mạng)

**Wireshark dùng để làm gì trong dự án này?**
* Bắt gói tin TCP/HTTP thực tế đang đi qua card mạng của máy tính.
* So sánh đối chiếu: gói tin mà Proxy của bạn gửi đi có đúng cấu trúc chuẩn HTTP hay không.
* Quan sát quá trình bắt tay TCP 3 bước (SYN → SYN-ACK → ACK) khi Proxy kết nối đến Web Server.

**Cài đặt trên Windows:**
1. Truy cập [wireshark.org/download](https://www.wireshark.org/download.html)
2. Tải bản **Windows x64 Installer** → Chạy file `.exe` và cài đặt bình thường.
3. Trong quá trình cài, chương trình sẽ hỏi cài thêm **Npcap** (driver bắt gói tin trên Windows) → Chọn **Install Npcap** → Nhấn Next cho đến khi xong.

**Mẹo sử dụng khi debug Proxy:**
* Mở Wireshark, chọn card mạng **Adapter for loopback traffic capture** (hoặc **Npcap Loopback Adapter**) vì Proxy chạy trên localhost `127.0.0.1`.
* Gõ bộ lọc: `tcp.port == 8888` để chỉ xem các gói tin đi qua cổng Proxy.

---

#### 4. Kiểm tra kết nối Socket bằng PowerShell

Trên Windows không có sẵn Netcat (`nc`) như Linux, nhưng bạn có thể dùng **PowerShell** tích hợp sẵn để kiểm tra tương tự:

**Kiểm tra Proxy có đang mở cổng 8888 không:**
```powershell
Test-NetConnection 127.0.0.1 -Port 8888
```
Nếu kết quả hiện `TcpTestSucceeded : True` nghĩa là Proxy đang chạy và lắng nghe đúng cổng.

**Gửi thủ công một HTTP Request thô đến Proxy (qua PowerShell):**
```powershell
$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 8888)
$stream = $client.GetStream()
$request = "GET http://example.com/ HTTP/1.1`r`nHost: example.com`r`n`r`n"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($request)
$stream.Write($bytes, 0, $bytes.Length)
Start-Sleep -Seconds 2
$buffer = New-Object byte[] 4096
$count = $stream.Read($buffer, 0, $buffer.Length)
[System.Text.Encoding]::ASCII.GetString($buffer, 0, $count)
$client.Close()
```

---

### D. Phần cứng cần chuẩn bị

| Thiết bị | Mục đích | Bắt buộc? |
|---|---|---|
| **1 Laptop/PC Windows** | Chạy Proxy Server + Trình duyệt Firefox trên cùng máy (giao tiếp qua `127.0.0.1`) | ✅ Bắt buộc |
| **1 Laptop/PC Windows thứ 2** | Để demo Proxy chạy thực tế trong mạng LAN: Máy A chạy Proxy, Máy B cấu hình Firefox trỏ đến IP máy A | 💡 Khuyến khích khi bảo vệ đồ án |
| **Điện thoại phát Wi-Fi Hotspot** | Tạo mạng LAN chung cho 2 máy tính khi demo tại phòng học (không phụ thuộc Wi-Fi trường) | 💡 Khuyến khích |

**⚠️ Lưu ý quan trọng về Windows Firewall:**
Khi chạy Proxy Server lần đầu, Windows Firewall sẽ hiện một hộp thoại hỏi cho phép Python truy cập mạng. Bạn **phải nhấn "Allow access"** (cho phép cả Private và Public network), nếu không trình duyệt sẽ không kết nối được đến Proxy.

Nếu lỡ bấm nhầm "Block", vào: **Control Panel → Windows Defender Firewall → Allow an app through firewall → Change settings → Tìm Python → Tích chọn cả 2 ô Private & Public → OK**.

---

## 🎬 Phần 4: Kịch Bản Demo Trước Giám Khảo

Khi bảo vệ đồ án, bạn có thể trình diễn theo thứ tự sau để tạo ấn tượng mạnh:

| Bước | Hành động | Điều giám khảo sẽ thấy |
|---|---|---|
| **1** | Mở CMD, chạy `python proxy.py` để khởi động Proxy Server | CMD hiển thị: `Proxy Server đang lắng nghe tại 127.0.0.1:8888...` |
| **2** | Mở Firefox (đã cấu hình proxy) → Truy cập `http://example.com` | Trang web hiển thị bình thường. Terminal của Proxy in ra log request HTTP. |
| **3** | Truy cập lại `http://example.com` lần 2 | Trang tải nhanh hơn rõ rệt. Terminal hiển thị: `CACHE HIT — Phục vụ từ bộ nhớ đệm`. |
| **4** | Truy cập một trang trong Blacklist (ví dụ: `facebook.com`) | Firefox hiển thị trang HTML cảnh báo 403 do nhóm tự thiết kế. Terminal hiển thị: `BLOCKED — facebook.com`. |
| **5** | Truy cập trang HTTPS (ví dụ: `https://www.google.com`) | Trang Google hiển thị bình thường. Terminal hiển thị: `HTTPS CONNECT TUNNEL — google.com:443`. |
| **6** | Mở Dashboard trên trình duyệt khác (`http://localhost:5000`) | Biểu đồ hiển thị tỷ lệ Cache Hit/Miss, danh sách URL đã truy cập, dung lượng tiết kiệm. |
