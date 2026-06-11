"""
rate_limiter.py — Module giới hạn tốc độ yêu cầu theo IP (Rate Limiting).

Kiến thức mạng áp dụng:
- HTTP Status Code 429 Too Many Requests (RFC 6585)
- Header Retry-After: thông báo thời gian chờ cho client
- Thuật toán Sliding Window: đếm số request trong cửa sổ thời gian trượt
- Chống tấn công từ chối dịch vụ (DDoS Mitigation)
- Quality of Service (QoS): đảm bảo công bằng tài nguyên giữa các client

Cơ chế hoạt động:
1. Mỗi client IP có một bộ đếm request và danh sách timestamp.
2. Khi nhận request mới, loại bỏ các timestamp cũ hơn cửa sổ thời gian.
3. Nếu số request còn lại >= giới hạn → trả về 429 Too Many Requests.
4. Thread-safe nhờ sử dụng threading.Lock().
"""

import os
import threading
import time
from collections import defaultdict

import config


class RateLimiter:
    """Giới hạn số lượng request mỗi IP trong một khoảng thời gian (Sliding Window)."""

    def __init__(self):
        self._lock = threading.Lock()
        # Dict lưu danh sách timestamp request cho mỗi IP
        # { "192.168.1.5": [timestamp1, timestamp2, ...] }
        self._requests: dict[str, list[float]] = defaultdict(list)
        # Thống kê
        self._total_limited = 0

    def is_rate_limited(self, client_ip: str) -> tuple[bool, int]:
        """
        Kiểm tra client_ip có bị giới hạn tốc độ không.

        Returns: (is_limited: bool, retry_after_seconds: int)
        - Nếu rate limiting bị tắt (max_requests <= 0): luôn trả (False, 0)
        - Nếu chưa vượt ngưỡng: ghi nhận request và trả (False, 0)
        - Nếu vượt ngưỡng: trả (True, retry_after_seconds)
        """
        max_requests = config.RATE_LIMIT_MAX_REQUESTS
        window = config.RATE_LIMIT_WINDOW

        # Tắt rate limiting nếu max_requests <= 0
        if max_requests <= 0:
            return False, 0

        current_time = time.time()

        with self._lock:
            # Lấy danh sách timestamp của IP này
            timestamps = self._requests[client_ip]

            # Loại bỏ các timestamp nằm ngoài cửa sổ thời gian (Sliding Window)
            window_start = current_time - window
            self._requests[client_ip] = [
                t for t in timestamps if t > window_start
            ]
            timestamps = self._requests[client_ip]

            if len(timestamps) >= max_requests:
                # Đã vượt ngưỡng → tính thời gian chờ
                oldest_in_window = timestamps[0]
                retry_after = int(oldest_in_window + window - current_time) + 1
                retry_after = max(retry_after, 1)
                self._total_limited += 1
                return True, retry_after

            # Chưa vượt ngưỡng → ghi nhận request mới
            timestamps.append(current_time)
            return False, 0

    def get_stats(self) -> dict:
        """Trả về thống kê rate limiting."""
        with self._lock:
            active_ips = len(self._requests)
            return {
                "total_rate_limited": self._total_limited,
                "active_tracked_ips": active_ips,
                "max_requests": config.RATE_LIMIT_MAX_REQUESTS,
                "window_seconds": config.RATE_LIMIT_WINDOW,
            }

    def get_rate_limited_page(self, client_ip: str, retry_after: int) -> bytes:
        """Tạo HTTP response 429 với trang HTML cảnh báo."""
        template_path = os.path.join(config.BASE_DIR, "templates", "rate_limited.html")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()
            html = html.replace("{{CLIENT_IP}}", client_ip)
            html = html.replace("{{RETRY_AFTER}}", str(retry_after))
            html = html.replace("{{MAX_REQUESTS}}", str(config.RATE_LIMIT_MAX_REQUESTS))
            html = html.replace("{{WINDOW}}", str(config.RATE_LIMIT_WINDOW))
        except FileNotFoundError:
            html = f"""<!DOCTYPE html>
<html><head><title>429 Too Many Requests</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px;">
<h1>⏱️ Quá Nhiều Yêu Cầu</h1>
<p>IP <b>{client_ip}</b> đã gửi quá nhiều request.</p>
<p>Vui lòng thử lại sau <b>{retry_after}</b> giây.</p>
</body></html>"""

        body = html.encode("utf-8")
        header = (
            "HTTP/1.1 429 Too Many Requests\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Retry-After: {retry_after}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        return header.encode("utf-8") + body

    def cleanup(self):
        """Dọn dẹp các IP không còn hoạt động (gọi định kỳ)."""
        current_time = time.time()
        window = config.RATE_LIMIT_WINDOW

        with self._lock:
            expired_ips = [
                ip for ip, timestamps in self._requests.items()
                if not timestamps or timestamps[-1] < current_time - window
            ]
            for ip in expired_ips:
                del self._requests[ip]
