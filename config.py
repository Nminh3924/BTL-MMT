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
# Traffic Shaping & Failover
# ──────────────────────────────────────────────
BANDWIDTH_LIMIT = 0           # Giới hạn băng thông (bytes/giây), 0 là không giới hạn
SIMULATE_FAILOVER = False     # Giả lập lỗi trên cổng mạng chính
OUTGOING_INTERFACES = [
    {"name": "Primary Connection", "ip": "0.0.0.0"},
    {"name": "Backup Connection", "ip": "0.0.0.0"}  # Trong thực tế, đổi thành IP của card thứ 2 (ví dụ: "192.168.1.50")
]

