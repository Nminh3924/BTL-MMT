"""
config.py — Tập trung tất cả cấu hình cho Web Proxy Server.
Thay đổi giá trị tại đây thay vì sửa trực tiếp trong code.
"""

import os

# ──────────────────────────────────────────────
# Proxy Server
# ──────────────────────────────────────────────
PROXY_HOST = "0.0.0.0"       # Lắng nghe trên tất cả interfaces
PROXY_PORT = 8888             # Cổng proxy
BACKLOG = 50                  # Số kết nối chờ tối đa trong hàng đợi

# ──────────────────────────────────────────────
# Network
# ──────────────────────────────────────────────
BUFFER_SIZE = 8192            # Kích thước buffer đọc socket (bytes)
SOCKET_TIMEOUT = 30           # Timeout cho mỗi socket connection (giây)
TUNNEL_TIMEOUT = 60           # Timeout cho HTTPS tunnel (giây)

# ──────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
MAX_CACHE_SIZE = 500 * 1024 * 1024   # 500 MB giới hạn dung lượng cache
CACHE_DEFAULT_TTL = 3600             # TTL mặc định 1 giờ (giây) nếu server không chỉ định

# ──────────────────────────────────────────────
# Web Filter
# ──────────────────────────────────────────────
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.txt")
ADLIST_FILE = os.path.join(BASE_DIR, "adlist.txt")

# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "proxy.log")
MAX_LOG_ENTRIES = 1000        # Số lượng log entry giữ trong RAM cho dashboard

# ──────────────────────────────────────────────
# Traffic Shaping & Server Outage Simulation
# ──────────────────────────────────────────────
BANDWIDTH_LIMIT = 0           # Giới hạn băng thông (bytes/giây), 0 là không giới hạn
SIMULATE_HTTP_ERROR = False      # Bật/tắt giả lập lỗi HTTP phản hồi
SIMULATE_HTTP_ERROR_CODE = 503   # Mã lỗi giả lập mặc định (403, 404, 500, 503, 504)


# ──────────────────────────────────────────────
# Proxy Authentication (RFC 7235)
# ──────────────────────────────────────────────
AUTH_ENABLED = False           # Bật/tắt xác thực proxy
AUTH_USERNAME = "admin"        # Tên đăng nhập mặc định
AUTH_PASSWORD = "proxy123"     # Mật khẩu mặc định
AUTH_REALM = "Custom Proxy Server"  # Tên hiển thị trên dialog đăng nhập trình duyệt

# ──────────────────────────────────────────────
# Rate Limiting (RFC 6585 — Chống DDoS)
# ──────────────────────────────────────────────
RATE_LIMIT_MAX_REQUESTS = 0    # Số request tối đa mỗi IP trong cửa sổ thời gian, 0 = tắt
RATE_LIMIT_WINDOW = 60         # Cửa sổ thời gian (giây), mặc định 60 giây

