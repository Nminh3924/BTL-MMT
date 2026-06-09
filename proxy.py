"""
proxy.py — Custom Web Proxy Server (Entry Point)

Đây là chương trình chính của dự án. Khi chạy, Proxy Server sẽ:
1. Lắng nghe kết nối TCP trên cổng 8888 (cấu hình trong config.py).
2. Nhận HTTP/HTTPS Request từ trình duyệt (Browser).
3. Kiểm tra Web Filter (blacklist/adlist) → chặn nếu domain bị cấm.
4. Kiểm tra Cache → trả từ cache nếu có (CACHE HIT).
5. Chuyển tiếp Request đến Web Server gốc → nhận Response → lưu cache → trả về Browser.
6. Với HTTPS: thiết lập Tunnel (CONNECT method) để truyền byte thô 2 chiều.
7. Ghi log mọi request vào logger + dashboard.

Kiến thức mạng áp dụng:
- TCP Socket Programming (Tầng Giao Vận)
- HTTP/1.1 Request/Response parsing (Tầng Ứng Dụng)
- HTTPS CONNECT Tunneling (SSL/TLS)
- Web Caching (RFC 7234)
- Application-level Firewall (Web Filter)

Cách chạy:
    python proxy.py

Cách test:
    curl -x http://127.0.0.1:8888 http://example.com -v
"""

import os
import signal
import socket
import select
import sys
import threading
import time

import config
from web_filter import WebFilter
from cache_manager import CacheManager
from logger import ProxyLogger


# ════════════════════════════════════════════════════════
# Module Globals
# ════════════════════════════════════════════════════════
web_filter = WebFilter()
cache_manager = CacheManager()
proxy_logger = ProxyLogger()
server_socket: socket.socket | None = None
running = True


# ════════════════════════════════════════════════════════
# HTTP Parser Utilities
# ════════════════════════════════════════════════════════

def parse_request_line(raw_request: bytes) -> tuple[str, str, str]:
    """
    Phân tích dòng đầu tiên của HTTP Request (Request Line).

    Ví dụ input:  b"GET http://example.com/path HTTP/1.1\\r\\n..."
    Output:       ("GET", "http://example.com/path", "HTTP/1.1")

    Ví dụ CONNECT: b"CONNECT www.google.com:443 HTTP/1.1\\r\\n..."
    Output:         ("CONNECT", "www.google.com:443", "HTTP/1.1")
    """
    try:
        # Lấy dòng đầu tiên
        first_line = raw_request.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ", 2)
        if len(parts) == 3:
            return parts[0].upper(), parts[1], parts[2]
        elif len(parts) == 2:
            return parts[0].upper(), parts[1], "HTTP/1.1"
    except Exception:
        pass
    return "", "", ""


def parse_headers(raw_request: bytes) -> dict[str, str]:
    """
    Phân tích các HTTP Header từ raw request.
    Trả về dict với key là tên header (lowercase), value là giá trị.
    """
    headers = {}
    try:
        # Tách header section (trước \r\n\r\n)
        header_section = raw_request.split(b"\r\n\r\n")[0]
        lines = header_section.split(b"\r\n")[1:]  # Bỏ request line
        for line in lines:
            decoded = line.decode("utf-8", errors="replace")
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                headers[key.strip().lower()] = value.strip()
    except Exception:
        pass
    return headers


def extract_host_port(method: str, url: str, headers: dict) -> tuple[str, int]:
    """
    Trích xuất hostname và port từ request.

    Với CONNECT:  "www.google.com:443"  → ("www.google.com", 443)
    Với GET:      "http://example.com/path" → ("example.com", 80)
    Fallback:     Đọc từ header Host
    """
    hostname = ""
    port = 80

    if method == "CONNECT":
        # CONNECT host:port
        if ":" in url:
            hostname, port_str = url.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 443
        else:
            hostname = url
            port = 443
    else:
        # HTTP: "http://host:port/path"
        if url.startswith("http://"):
            url_body = url[7:]  # bỏ "http://"
        elif url.startswith("https://"):
            url_body = url[8:]
            port = 443
        else:
            url_body = url

        # Tách host:port khỏi path
        slash_idx = url_body.find("/")
        if slash_idx != -1:
            host_part = url_body[:slash_idx]
        else:
            host_part = url_body

        if ":" in host_part:
            hostname, port_str = host_part.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 80
        else:
            hostname = host_part

    # Fallback: dùng Host header
    if not hostname:
        host_header = headers.get("host", "")
        if ":" in host_header:
            hostname, port_str = host_header.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        else:
            hostname = host_header

    return hostname.strip(), port


def build_relative_request(raw_request: bytes, url: str) -> bytes:
    """
    Chuyển absolute URL trong request thành relative path.

    Browser gửi qua proxy: "GET http://example.com/page HTTP/1.1"
    Server gốc cần nhận:   "GET /page HTTP/1.1"

    Đây là yêu cầu của chuẩn HTTP/1.1: khi proxy forward request
    đến origin server, URL phải là relative path.
    """
    try:
        if url.startswith("http://"):
            # Tìm vị trí bắt đầu path sau host
            url_body = url[7:]
            slash_idx = url_body.find("/")
            if slash_idx != -1:
                relative_path = url_body[slash_idx:]
            else:
                relative_path = "/"
        elif url.startswith("https://"):
            url_body = url[8:]
            slash_idx = url_body.find("/")
            if slash_idx != -1:
                relative_path = url_body[slash_idx:]
            else:
                relative_path = "/"
        else:
            return raw_request  # Đã là relative

        # Thay thế URL trong request line
        first_line_end = raw_request.find(b"\r\n")
        old_first_line = raw_request[:first_line_end]
        parts = old_first_line.split(b" ", 2)
        if len(parts) >= 3:
            new_first_line = parts[0] + b" " + relative_path.encode() + b" " + parts[2]
            return new_first_line + raw_request[first_line_end:]
    except Exception:
        pass
    return raw_request


def parse_response_headers(raw_response: bytes) -> tuple[int, dict[str, str], int]:
    """
    Phân tích HTTP Response: status code, headers, vị trí bắt đầu body.

    Returns: (status_code, headers_dict, header_end_position)
    """
    status_code = 0
    headers = {}
    header_end = raw_response.find(b"\r\n\r\n")
    if header_end == -1:
        return 0, {}, -1

    header_section = raw_response[:header_end]
    lines = header_section.split(b"\r\n")

    # Parse status line: "HTTP/1.1 200 OK"
    if lines:
        status_line = lines[0].decode("utf-8", errors="replace")
        parts = status_line.split(" ", 2)
        if len(parts) >= 2:
            try:
                status_code = int(parts[1])
            except ValueError:
                pass

    # Parse headers
    for line in lines[1:]:
        decoded = line.decode("utf-8", errors="replace")
        if ":" in decoded:
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    return status_code, headers, header_end + 4  # +4 cho \r\n\r\n


def connect_to_origin(hostname: str, port: int) -> tuple[socket.socket, str]:
    """
    Kết nối tới origin server sử dụng cơ chế failover qua nhiều interface.
    Nếu config.SIMULATE_FAILOVER = True, ta giả lập lỗi kết nối trên interface đầu tiên.
    Trả về (connected_socket, interface_name).
    """
    last_err = None
    for i, iface in enumerate(config.OUTGOING_INTERFACES):
        name = iface["name"]
        ip = iface["ip"]
        
        # Giả lập lỗi ở interface đầu tiên (chỉ khi có ít nhất 2 interface cấu hình)
        if config.SIMULATE_FAILOVER and i == 0 and len(config.OUTGOING_INTERFACES) > 1:
            print(f"[Failover] Giả lập lỗi kết nối trên giao diện chính: {name}")
            last_err = socket.error("Simulated primary interface failure")
            continue
            
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(config.SOCKET_TIMEOUT)
        try:
            if ip and ip != "0.0.0.0":
                sock.bind((ip, 0))
            sock.connect((hostname, port))
            return sock, name
        except Exception as e:
            print(f"[Failover] Không thể kết nối qua {name} ({ip if ip else 'default'}): {e}")
            last_err = e
            try:
                sock.close()
            except Exception:
                pass
    raise last_err if last_err else socket.error("Tất cả các giao diện mạng đều kết nối thất bại")


def send_throttled(client_sock: socket.socket, data: bytes, limit_bytes_per_sec: int):
    """
    Gửi dữ liệu qua socket client với giới hạn băng thông (throttling).
    """
    if limit_bytes_per_sec <= 0 or not data:
        client_sock.sendall(data)
        return

    chunk_size = 4096
    total_sent = 0
    start_time = time.time()
    
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        client_sock.sendall(chunk)
        total_sent += len(chunk)
        
        expected_time = total_sent / limit_bytes_per_sec
        elapsed_time = time.time() - start_time
        sleep_time = expected_time - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)


# ════════════════════════════════════════════════════════
# Request Handlers
# ════════════════════════════════════════════════════════

def _inject_connection_close(raw_request: bytes) -> bytes:
    """
    Chèn header 'Connection: close' vào request để yêu cầu Web Server
    đóng kết nối ngay sau khi gửi xong response.
    Điều này giúp proxy biết khi nào đã nhận hết dữ liệu mà không phải
    chờ socket timeout.
    """
    # Thay thế Connection header hiện có (nếu có) hoặc thêm mới
    if b"Connection:" in raw_request or b"connection:" in raw_request:
        # Thay thế giá trị Connection header
        lines = raw_request.split(b"\r\n")
        new_lines = []
        for line in lines:
            if line.lower().startswith(b"connection:"):
                new_lines.append(b"Connection: close")
            else:
                new_lines.append(line)
        return b"\r\n".join(new_lines)
    else:
        # Chèn trước \r\n\r\n cuối cùng
        header_end = raw_request.find(b"\r\n\r\n")
        if header_end != -1:
            return (raw_request[:header_end] +
                    b"\r\nConnection: close" +
                    raw_request[header_end:])
        return raw_request


def _recv_http_response(server_sock: socket.socket) -> bytes:
    """
    Nhận toàn bộ HTTP Response từ Web Server một cách thông minh.

    Chiến lược đọc (theo thứ tự ưu tiên):
    1. Đọc headers trước → tìm Content-Length.
    2. Nếu có Content-Length → đọc đúng số bytes body.
    3. Nếu không có → đọc cho đến khi server đóng kết nối (Connection: close).
    """
    # Bước 1: Đọc cho đến khi nhận được hết phần header (\r\n\r\n)
    response_data = b""
    while b"\r\n\r\n" not in response_data:
        try:
            chunk = server_sock.recv(config.BUFFER_SIZE)
            if not chunk:
                return response_data
            response_data += chunk
        except socket.timeout:
            return response_data

    # Bước 2: Parse headers để tìm Content-Length
    header_end_idx = response_data.find(b"\r\n\r\n") + 4
    header_section = response_data[:header_end_idx].decode("utf-8", errors="replace").lower()

    content_length = -1
    for line in header_section.split("\r\n"):
        if line.startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            break

    # Bước 3: Đọc body
    if content_length >= 0:
        # Biết chính xác kích thước body → đọc đủ rồi dừng
        body_received = len(response_data) - header_end_idx
        remaining = content_length - body_received
        while remaining > 0:
            try:
                chunk = server_sock.recv(min(config.BUFFER_SIZE, remaining))
                if not chunk:
                    break
                response_data += chunk
                remaining -= len(chunk)
            except socket.timeout:
                break
    else:
        # Không có Content-Length → đọc cho đến khi server đóng kết nối
        # (do đã gửi Connection: close, server sẽ đóng sau khi gửi xong)
        server_sock.settimeout(5)  # Timeout ngắn hơn cho chế độ này
        while True:
            try:
                chunk = server_sock.recv(config.BUFFER_SIZE)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break

    return response_data


def handle_http_request(client_socket: socket.socket, method: str,
                        url: str, hostname: str, port: int,
                        raw_request: bytes, headers: dict, client_ip: str):
    """
    Xử lý HTTP Request (GET, POST, HEAD...).

    Luồng xử lý:
    1. Kiểm tra cache → nếu HIT, trả response từ cache.
    2. Nếu MISS → kết nối đến Web Server gốc, forward request.
    3. Nhận response → lưu vào cache (nếu được phép) → trả về browser.
    """
    start_time = time.time()
    response_size = 0
    status_code = 0
    cache_status = "MISS"
    out_iface = "-"

    try:
        # ──── Bước 1: Kiểm tra Cache ────
        hit, cached_data, cached_meta = cache_manager.get(url)

        if hit and cached_data:
            # CACHE HIT — trả dữ liệu từ cache
            send_throttled(client_socket, cached_data, config.BANDWIDTH_LIMIT)
            response_size = len(cached_data)
            cache_status = "HIT"
            out_iface = "Cache"
            # Parse status code từ cached data
            sc, _, _ = parse_response_headers(cached_data)
            status_code = sc if sc else 200
        else:
            # ──── Bước 2: Forward request đến Web Server ────
            # Chuyển URL absolute → relative
            forwarded_request = build_relative_request(raw_request, url)
            # Chèn Connection: close để server đóng kết nối sau khi gửi response
            forwarded_request = _inject_connection_close(forwarded_request)

            server_sock = None
            try:
                server_sock, out_iface = connect_to_origin(hostname, port)
                server_sock.sendall(forwarded_request)

                # ──── Bước 3: Nhận toàn bộ Response (thông minh) ────
                response_data = _recv_http_response(server_sock)

                if response_data:
                    # Parse response headers
                    status_code, resp_headers, body_start = parse_response_headers(response_data)

                    # Gửi response về browser với giới hạn băng thông (throttling)
                    send_throttled(client_socket, response_data, config.BANDWIDTH_LIMIT)
                    response_size = len(response_data)

                    # ──── Bước 4: Lưu vào Cache ────
                    if status_code == 200 and body_start > 0:
                        cache_manager.put(url, response_data, resp_headers)

                    cache_status = "MISS"
                else:
                    # Server không trả response
                    error_response = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"
                    client_socket.sendall(error_response)
                    status_code = 502
                    cache_status = "ERROR"

            finally:
                if server_sock:
                    try:
                        server_sock.close()
                    except Exception:
                        pass

    except socket.timeout:
        try:
            error_response = b"HTTP/1.1 504 Gateway Timeout\r\nContent-Length: 0\r\n\r\n"
            client_socket.sendall(error_response)
        except Exception:
            pass
        status_code = 504
        cache_status = "ERROR"
    except (ConnectionRefusedError, socket.gaierror) as e:
        try:
            error_response = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"
            client_socket.sendall(error_response)
        except Exception:
            pass
        status_code = 502
        cache_status = "ERROR"
    except Exception as e:
        try:
            error_response = b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n"
            client_socket.sendall(error_response)
        except Exception:
            pass
        status_code = 500
        cache_status = "ERROR"

    # ──── Ghi Log ────
    elapsed_ms = (time.time() - start_time) * 1000
    proxy_logger.log({
        "timestamp": time.time(),
        "client_ip": client_ip,
        "method": method,
        "url": url,
        "hostname": hostname,
        "status_code": status_code,
        "cache_status": cache_status,
        "response_size": response_size,
        "response_time_ms": elapsed_ms,
        "outgoing_interface": out_iface,
    })


def handle_https_tunnel(client_socket: socket.socket, hostname: str,
                        port: int, client_ip: str):
    """
    Xử lý HTTPS Request bằng CONNECT Tunneling.

    Cơ chế hoạt động (RFC 7231 — CONNECT method):
    1. Browser gửi: "CONNECT www.google.com:443 HTTP/1.1"
    2. Proxy tạo TCP connection đến www.google.com:443.
    3. Proxy gửi lại browser: "HTTP/1.1 200 Connection Established"
    4. Từ đây, Proxy chỉ đóng vai trò "ống dẫn" (tunnel):
       - Mọi bytes từ browser → chuyển thẳng đến server.
       - Mọi bytes từ server → chuyển thẳng đến browser.
    5. Proxy KHÔNG đọc/giải mã nội dung (vì đã được mã hóa SSL/TLS).

    Đây là cách proxy tôn trọng tính bảo mật End-to-End của HTTPS.
    """
    start_time = time.time()
    out_iface = "-"
    server_sock = None

    try:
        # Kết nối đến Web Server gốc sử dụng failover
        server_sock, out_iface = connect_to_origin(hostname, port)

        # Gửi phản hồi 200 cho browser → tunnel đã sẵn sàng
        client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

        # Thiết lập tunnel: truyền byte thô 2 chiều
        client_socket.setblocking(False)
        server_sock.setblocking(False)

        sockets = [client_socket, server_sock]
        tunnel_active = True
        total_bytes = 0
        total_bytes_sent_to_client = 0
        tunnel_start_time = time.time()

        while tunnel_active and running:
            try:
                # select() chờ dữ liệu từ 1 trong 2 socket
                readable, _, exceptional = select.select(
                    sockets, [], sockets, config.TUNNEL_TIMEOUT
                )

                if exceptional:
                    break

                if not readable:
                    # Timeout — không có dữ liệu, đóng tunnel
                    break

                for sock in readable:
                    try:
                        data = sock.recv(config.BUFFER_SIZE)
                        if not data:
                            tunnel_active = False
                            break

                        # Forward dữ liệu sang socket đối diện
                        if sock is client_socket:
                            server_sock.sendall(data)
                        else:
                            # Server gửi về client (Download) -> giới hạn tốc độ ở đây
                            client_socket.sendall(data)
                            total_bytes_sent_to_client += len(data)
                            
                            limit = config.BANDWIDTH_LIMIT
                            if limit > 0:
                                expected_time = total_bytes_sent_to_client / limit
                                elapsed = time.time() - tunnel_start_time
                                sleep_time = expected_time - elapsed
                                if sleep_time > 0:
                                    time.sleep(sleep_time)

                        total_bytes += len(data)
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        tunnel_active = False
                        break

            except (ValueError, OSError):
                break

        if server_sock:
            try:
                server_sock.close()
            except Exception:
                pass

        # Ghi log
        elapsed_ms = (time.time() - start_time) * 1000
        proxy_logger.log({
            "timestamp": time.time(),
            "client_ip": client_ip,
            "method": "CONNECT",
            "url": f"https://{hostname}:{port}",
            "hostname": hostname,
            "status_code": 200,
            "cache_status": "TUNNEL",
            "response_size": total_bytes,
            "response_time_ms": elapsed_ms,
            "outgoing_interface": out_iface,
        })

    except socket.timeout:
        try:
            client_socket.sendall(b"HTTP/1.1 504 Gateway Timeout\r\n\r\n")
        except Exception:
            pass
    except (ConnectionRefusedError, socket.gaierror) as e:
        try:
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except Exception:
            pass
        proxy_logger.log({
            "timestamp": time.time(),
            "client_ip": client_ip,
            "method": "CONNECT",
            "url": f"https://{hostname}:{port}",
            "hostname": hostname,
            "status_code": 502,
            "cache_status": "ERROR",
            "response_size": 0,
            "response_time_ms": (time.time() - start_time) * 1000,
            "outgoing_interface": out_iface,
        })
    except Exception as e:
        pass
    finally:
        if server_sock:
            try:
                server_sock.close()
            except Exception:
                pass


# ════════════════════════════════════════════════════════
# Client Connection Handler (chạy trên thread riêng)
# ════════════════════════════════════════════════════════

def handle_client(client_socket: socket.socket, client_addr: tuple):
    """
    Xử lý 1 kết nối từ browser. Hàm này chạy trên thread riêng.

    Luồng xử lý:
    1. Đọc raw request từ browser.
    2. Parse request line và headers.
    3. Trích xuất hostname, port.
    4. Kiểm tra Web Filter → chặn nếu cần.
    5. Phân loại: CONNECT (HTTPS) → tunnel, còn lại (HTTP) → forward + cache.
    """
    client_ip = client_addr[0]

    try:
        client_socket.settimeout(config.SOCKET_TIMEOUT)

        # ──── Bước 1: Đọc request từ browser ────
        raw_request = client_socket.recv(config.BUFFER_SIZE)
        if not raw_request:
            return

        # ──── Bước 2: Parse request ────
        method, url, http_version = parse_request_line(raw_request)
        if not method or not url:
            return

        headers = parse_headers(raw_request)
        hostname, port = extract_host_port(method, url, headers)

        if not hostname:
            return

        # ──── Bước 3: Kiểm tra Web Filter ────
        blocked, reason = web_filter.should_block(hostname)
        if blocked:
            # Gửi trang 403 tự thiết kế
            blocked_response = web_filter.get_blocked_page(hostname, reason)
            client_socket.sendall(blocked_response)

            proxy_logger.log({
                "timestamp": time.time(),
                "client_ip": client_ip,
                "method": method,
                "url": url,
                "hostname": hostname,
                "status_code": 403,
                "cache_status": "BLOCKED",
                "response_size": len(blocked_response),
                "response_time_ms": 0,
            })
            return

        # ──── Bước 4: Xử lý theo loại request ────
        if method == "CONNECT":
            # HTTPS Tunneling
            handle_https_tunnel(client_socket, hostname, port, client_ip)
        else:
            # HTTP Request (GET, POST, HEAD...)
            handle_http_request(
                client_socket, method, url, hostname, port,
                raw_request, headers, client_ip
            )

    except socket.timeout:
        pass
    except Exception as e:
        print(f"[Proxy] Lỗi xử lý client {client_ip}: {e}")
    finally:
        try:
            client_socket.close()
        except Exception:
            pass


# ════════════════════════════════════════════════════════
# Dashboard Integration
# ════════════════════════════════════════════════════════

def start_dashboard():
    """Khởi động Flask Dashboard trong thread riêng."""
    try:
        from dashboard import create_app
        app = create_app(proxy_logger, cache_manager, web_filter)
        print(f"\n🌐 Dashboard đang chạy tại: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}\n")
        app.run(
            host=config.DASHBOARD_HOST,
            port=config.DASHBOARD_PORT,
            debug=False,
            use_reloader=False,  # Quan trọng: tắt reloader khi chạy trong thread
        )
    except ImportError:
        print("[Dashboard] Flask chưa được cài đặt. Chạy: pip install flask")
    except Exception as e:
        print(f"[Dashboard] Lỗi khởi động: {e}")


# ════════════════════════════════════════════════════════
# Main Server Loop
# ════════════════════════════════════════════════════════

def shutdown_handler(signum, frame):
    """Xử lý tắt server gracefully khi nhận Ctrl+C."""
    global running
    print("\n\n🛑 Đang tắt Proxy Server...")
    running = False
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass
    sys.exit(0)


def main():
    global server_socket

    # Đăng ký signal handler cho Ctrl+C
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Tạo thư mục cần thiết
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # ──── Khởi động Dashboard (thread riêng) ────
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    # ──── Khởi động TCP Server Socket ────
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((config.PROXY_HOST, config.PROXY_PORT))
    server_socket.listen(config.BACKLOG)
    server_socket.settimeout(1.0)  # Timeout để kiểm tra flag 'running' định kỳ

    print("=" * 65)
    print("  🚀 CUSTOM WEB PROXY SERVER")
    print("=" * 65)
    print(f"  📡 Proxy đang lắng nghe tại: {config.PROXY_HOST}:{config.PROXY_PORT}")
    print(f"  🌐 Dashboard:                http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    print(f"  💾 Thư mục Cache:            {config.CACHE_DIR}")
    print(f"  📋 File Log:                 {config.LOG_FILE}")
    print(f"  ⛔ Blacklist:                {len(web_filter._blacklist)} domains")
    print(f"  🚫 Adlist:                   {len(web_filter._adlist)} domains")
    print("=" * 65)
    print("  Nhấn Ctrl+C để dừng server")
    print("=" * 65)
    print()

    # ──── Accept Loop ────
    while running:
        try:
            client_socket, client_addr = server_socket.accept()
            # Spawn daemon thread cho mỗi kết nối
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_addr),
                daemon=True,
            )
            thread.start()
        except socket.timeout:
            continue  # Quay lại kiểm tra flag 'running'
        except OSError:
            if running:
                print("[Proxy] Lỗi accept connection")
            break


if __name__ == "__main__":
    main()
