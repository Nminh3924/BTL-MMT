"""
web_filter.py — Module lọc tên miền (Blacklist) và chặn quảng cáo (Ad Blocker).

Hoạt động ở tầng ứng dụng (Application Layer):
- Phân tích trường Host trong HTTP Request Header.
- So khớp với danh sách đen (blacklist) và danh sách host quảng cáo (adlist).
- Hỗ trợ matching subdomain: nếu chặn "facebook.com" thì "m.facebook.com" cũng bị chặn.
"""

import os
import threading

import config


class WebFilter:
    """Bộ lọc tên miền — kiểm tra domain có nằm trong blacklist/adlist hay không."""

    def __init__(self):
        self._lock = threading.Lock()
        self._blacklist: set[str] = set()
        self._adlist: set[str] = set()
        self.reload()

    # ──────────────────── Public API ────────────────────

    def is_blocked(self, hostname: str) -> bool:
        """Kiểm tra hostname có bị chặn bởi blacklist không."""
        hostname = hostname.lower().strip()
        with self._lock:
            return self._match_domain(hostname, self._blacklist)

    def is_ad(self, hostname: str) -> bool:
        """Kiểm tra hostname có phải host quảng cáo không."""
        hostname = hostname.lower().strip()
        with self._lock:
            return self._match_domain(hostname, self._adlist)

    def should_block(self, hostname: str) -> tuple[bool, str]:
        """
        Kiểm tra tổng hợp: domain có bị chặn không và lý do.
        Returns: (blocked: bool, reason: str)
        """
        hostname = hostname.lower().strip()
        with self._lock:
            if self._match_domain(hostname, self._blacklist):
                return True, "BLACKLISTED"
            if self._match_domain(hostname, self._adlist):
                return True, "AD_BLOCKED"
        return False, ""

    def reload(self):
        """Tải lại danh sách từ file (hỗ trợ hot-reload)."""
        with self._lock:
            self._blacklist = self._load_file(config.BLACKLIST_FILE)
            self._adlist = self._load_file(config.ADLIST_FILE)
        print(f"[WebFilter] Đã tải {len(self._blacklist)} domain blacklist, "
              f"{len(self._adlist)} domain adlist")

    # ──────────────────── Internal ────────────────────

    @staticmethod
    def _load_file(filepath: str) -> set[str]:
        """Đọc file danh sách domain (mỗi dòng 1 domain, bỏ qua dòng trống và comment #)."""
        domains = set()
        if not os.path.exists(filepath):
            return domains
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().lower()
                    # Bỏ qua dòng trống và comment
                    if line and not line.startswith("#"):
                        domains.add(line)
        except Exception as e:
            print(f"[WebFilter] Lỗi đọc file {filepath}: {e}")
        return domains

    @staticmethod
    def _match_domain(hostname: str, domain_set: set[str]) -> bool:
        """
        Kiểm tra hostname có khớp với bất kỳ domain nào trong set không.
        Hỗ trợ subdomain matching:
        - "facebook.com" khớp với "facebook.com" và "m.facebook.com"
        - "m.facebook.com" chỉ khớp với "m.facebook.com", KHÔNG khớp "facebook.com"
        """
        if hostname in domain_set:
            return True
        # Kiểm tra subdomain: tách dần từ trái sang phải
        parts = hostname.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in domain_set:
                return True
        return False

    def get_blocked_page(self, hostname: str, reason: str) -> bytes:
        """Tạo HTTP response 403 với trang HTML cảnh báo."""
        # Đọc template blocked.html
        template_path = os.path.join(config.BASE_DIR, "templates", "blocked.html")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()
            # Thay thế placeholder
            html = html.replace("{{DOMAIN}}", hostname)
            html = html.replace("{{REASON}}", reason)
        except FileNotFoundError:
            # Fallback nếu không có template
            html = f"""<!DOCTYPE html>
<html><head><title>403 Forbidden</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px;">
<h1>⛔ Truy cập bị chặn</h1>
<p>Trang <b>{hostname}</b> đã bị chặn bởi hệ thống proxy.</p>
<p>Lý do: {reason}</p>
</body></html>"""

        body = html.encode("utf-8")
        header = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        return header.encode("utf-8") + body
