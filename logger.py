"""
logger.py — Module ghi nhật ký (Logging) và thống kê cho Proxy Server.

Sử dụng thread-safe queue để nhận log entries từ nhiều proxy threads
mà không gây xung đột khi ghi file hoặc cập nhật stats.
"""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime

import config


class ProxyLogger:
    """Ghi nhật ký request và tính toán thống kê thời gian thực."""

    def __init__(self):
        self._lock = threading.Lock()
        self._recent_logs: deque[dict] = deque(maxlen=config.MAX_LOG_ENTRIES)

        # Thống kê tổng hợp
        self._stats = {
            "total_requests": 0,
            "total_blocked": 0,
            "total_bytes_served": 0,
            "total_bytes_saved": 0,   # Bytes tiết kiệm nhờ cache
            "methods": {},             # {"GET": 100, "CONNECT": 50, ...}
            "status_codes": {},        # {"200": 80, "403": 10, ...}
            "domains": {},             # {"example.com": 15, ...}
            "cache_hits": 0,
            "cache_misses": 0,
            "total_rate_limited": 0,
        }

        # Tạo thư mục log
        os.makedirs(config.LOG_DIR, exist_ok=True)

        print(f"[Logger] Khởi tạo logger, log file: {config.LOG_FILE}")

    def log(self, entry: dict):
        """
        Ghi 1 log entry.

        entry = {
            "timestamp": float,        # time.time()
            "client_ip": str,          # IP client
            "method": str,             # GET, POST, CONNECT...
            "url": str,                # URL đầy đủ
            "hostname": str,           # Domain
            "status_code": int,        # 200, 403, 502...
            "cache_status": str,       # "HIT", "MISS", "BYPASS", "BLOCKED", "TUNNEL"
            "response_size": int,      # bytes
            "response_time_ms": float, # milliseconds
        }
        """
        # Thêm timestamp dạng đọc được
        entry["datetime"] = datetime.fromtimestamp(
            entry.get("timestamp", time.time())
        ).strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            # Lưu vào deque (tự xóa entry cũ khi đầy)
            self._recent_logs.appendleft(entry)

            # Cập nhật thống kê
            self._stats["total_requests"] += 1

            method = entry.get("method", "UNKNOWN")
            self._stats["methods"][method] = self._stats["methods"].get(method, 0) + 1

            status = str(entry.get("status_code", 0))
            self._stats["status_codes"][status] = self._stats["status_codes"].get(status, 0) + 1

            hostname = entry.get("hostname", "unknown")
            self._stats["domains"][hostname] = self._stats["domains"].get(hostname, 0) + 1

            cache_status = entry.get("cache_status", "")
            if cache_status in ("HIT", "OFFLINE_CACHE"):
                self._stats["cache_hits"] += 1
                self._stats["total_bytes_saved"] += entry.get("response_size", 0)
            elif cache_status == "MISS":
                self._stats["cache_misses"] += 1
            elif cache_status == "BLOCKED":
                self._stats["total_blocked"] += 1
            elif cache_status == "RATE_LIMITED":
                self._stats["total_rate_limited"] += 1

            self._stats["total_bytes_served"] += entry.get("response_size", 0)

        # In ra terminal (không cần lock)
        self._print_log(entry)

        # Ghi ra file (append)
        self._write_to_file(entry)

    def get_recent_logs(self, n: int = 50) -> list[dict]:
        """Trả về n log entries gần nhất."""
        with self._lock:
            return list(self._recent_logs)[:n]

    def get_stats(self) -> dict:
        """Trả về thống kê tổng hợp."""
        with self._lock:
            stats = self._stats.copy()
            # Tính cache hit rate
            total_cache = stats["cache_hits"] + stats["cache_misses"]
            stats["cache_hit_rate"] = (
                round(stats["cache_hits"] / total_cache * 100, 1)
                if total_cache > 0 else 0
            )
            # Top domains (sắp xếp theo số lần truy cập, lấy 10)
            stats["top_domains"] = sorted(
                stats["domains"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            # Format bytes đã tiết kiệm
            stats["bytes_saved_formatted"] = self._format_bytes(stats["total_bytes_saved"])
            stats["bytes_served_formatted"] = self._format_bytes(stats["total_bytes_served"])
            return stats

    # ──────────────────── Internal ────────────────────

    @staticmethod
    def _print_log(entry: dict):
        """In log entry ra terminal với format đẹp và có màu."""
        cache_status = entry.get("cache_status", "")
        method = entry.get("method", "?")
        url = entry.get("url", "?")
        status = entry.get("status_code", 0)
        size = entry.get("response_size", 0)
        time_ms = entry.get("response_time_ms", 0)
        dt = entry.get("datetime", "")

        # Emoji theo cache status
        status_icon = {
            "HIT": "💾 CACHE HIT ",
            "MISS": "🌐 CACHE MISS",
            "BLOCKED": "⛔ BLOCKED   ",
            "TUNNEL": "🔒 TUNNEL    ",
            "BYPASS": "⏩ BYPASS    ",
            "ERROR": "❌ ERROR     ",
            "RATE_LIMITED": "⏱️  RATE LIMIT",
            "AUTH_REQUIRED": "🔐 AUTH REQ  ",
            "OFFLINE_CACHE": "💾 OFFLINE CACHE",
            "SIMULATED": "⚠️ SIMULATED  ",
        }.get(cache_status, "   ???       ")

        # Rút gọn URL nếu quá dài
        display_url = url if len(url) <= 60 else url[:57] + "..."

        size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
        iface = entry.get("outgoing_interface", "")
        iface_str = f" [{iface}]" if iface else ""

        print(f"[{dt}] {status_icon}  {method:<7} {display_url:<60}  "
              f"→ {status}  ({size_str}, {time_ms:.0f}ms){iface_str}")

    def _write_to_file(self, entry: dict):
        """Ghi log entry ra file JSON Lines (mỗi dòng 1 JSON object)."""
        try:
            with open(config.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            print(f"[Logger] Lỗi ghi log file: {e}")

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Chuyển bytes thành format dễ đọc (KB, MB, GB)."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
