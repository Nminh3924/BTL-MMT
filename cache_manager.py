"""
cache_manager.py — Module quản lý bộ nhớ đệm (Web Cache) cho Proxy Server.

Kiến thức mạng áp dụng (RFC 7234 — HTTP Caching):
- Phân tích header Cache-Control (max-age, no-store, no-cache) để quyết định lưu trữ.
- Hỗ trợ Conditional GET với If-Modified-Since / ETag (HTTP 304 Not Modified).
- Chính sách eviction: LRU (Least Recently Used) + TTL (Time-To-Live).
- Giới hạn dung lượng tối đa (mặc định 500MB) để tránh cạn kiệt tài nguyên đĩa.

Cấu trúc lưu trữ trên đĩa:
    cache/
    ├── {md5_hash}.data    # Body của HTTP Response
    └── {md5_hash}.meta    # Metadata JSON (headers, timestamp, TTL, size, url)
"""

import hashlib
import json
import os
import threading
import time

import config


class CacheManager:
    """Quản lý cache trên ổ đĩa với LRU eviction và TTL expiration."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache_dir = config.CACHE_DIR
        self._max_size = config.MAX_CACHE_SIZE
        self._default_ttl = config.CACHE_DEFAULT_TTL

        # Tạo thư mục cache nếu chưa tồn tại
        os.makedirs(self._cache_dir, exist_ok=True)

        # Thống kê
        self.hits = 0
        self.misses = 0

        print(f"[Cache] Khởi tạo cache tại {self._cache_dir} "
              f"(giới hạn {self._max_size // (1024*1024)}MB)")

    # ──────────────────── Public API ────────────────────

    def get(self, url: str) -> tuple[bool, bytes | None, dict | None]:
        """
        Kiểm tra và đọc cache cho URL.

        Returns:
            (hit, response_data, meta)
            - hit=True, data=bytes, meta=dict  nếu cache hợp lệ (CACHE HIT)
            - hit=False, data=None, meta=dict   nếu cache hết hạn (cần revalidate)
            - hit=False, data=None, meta=None   nếu không có cache (CACHE MISS)
        """
        cache_hash = self._hash_url(url)
        meta_path = os.path.join(self._cache_dir, f"{cache_hash}.meta")
        data_path = os.path.join(self._cache_dir, f"{cache_hash}.data")

        with self._lock:
            if not os.path.exists(meta_path) or not os.path.exists(data_path):
                self.misses += 1
                return False, None, None

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.misses += 1
                return False, None, None

            # Kiểm tra TTL
            if self._is_expired(meta):
                self.misses += 1
                # Trả meta để caller có thể dùng If-Modified-Since revalidate
                return False, None, meta

            # Cache còn hạn — CACHE HIT
            try:
                with open(data_path, "rb") as f:
                    data = f.read()
            except OSError:
                self.misses += 1
                return False, None, None

            # Cập nhật last_accessed cho LRU
            meta["last_accessed"] = time.time()
            self._write_meta(meta_path, meta)

            self.hits += 1
            return True, data, meta

    def put(self, url: str, response_data: bytes, response_headers: dict):
        """
        Lưu response vào cache.

        Kiểm tra Cache-Control header trước khi lưu:
        - no-store → không lưu
        - max-age=N → TTL = N giây
        - Không có chỉ định → dùng TTL mặc định
        """
        # Kiểm tra có được phép cache không
        cache_control = response_headers.get("cache-control", "").lower()
        if "no-store" in cache_control:
            return
        if "private" in cache_control:
            return

        # Tính TTL
        ttl = self._parse_max_age(cache_control)
        if ttl is None:
            ttl = self._default_ttl

        # Không cache nếu TTL = 0
        if ttl <= 0:
            return

        cache_hash = self._hash_url(url)
        meta_path = os.path.join(self._cache_dir, f"{cache_hash}.meta")
        data_path = os.path.join(self._cache_dir, f"{cache_hash}.data")

        meta = {
            "url": url,
            "hash": cache_hash,
            "created_at": time.time(),
            "last_accessed": time.time(),
            "ttl": ttl,
            "size": len(response_data),
            "headers": response_headers,
            # Lưu lại để dùng cho Conditional GET (revalidation)
            "last_modified": response_headers.get("last-modified", ""),
            "etag": response_headers.get("etag", ""),
        }

        with self._lock:
            try:
                # Ghi data
                with open(data_path, "wb") as f:
                    f.write(response_data)
                # Ghi metadata
                self._write_meta(meta_path, meta)
                # Kiểm tra dung lượng và evict nếu cần
                self._evict_if_needed()
            except OSError as e:
                print(f"[Cache] Lỗi ghi cache cho {url}: {e}")

    def get_revalidation_headers(self, meta: dict) -> dict:
        """
        Tạo headers cho Conditional GET (revalidation).
        Dùng khi cache hết hạn nhưng vẫn muốn kiểm tra với server
        bằng If-Modified-Since hoặc If-None-Match (ETag).
        """
        headers = {}
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        return headers

    def refresh_ttl(self, url: str, new_headers: dict = None):
        """Cập nhật TTL cho cache entry (dùng khi nhận 304 Not Modified)."""
        cache_hash = self._hash_url(url)
        meta_path = os.path.join(self._cache_dir, f"{cache_hash}.meta")

        with self._lock:
            if not os.path.exists(meta_path):
                return
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["created_at"] = time.time()
                meta["last_accessed"] = time.time()
                if new_headers:
                    cache_control = new_headers.get("cache-control", "")
                    ttl = self._parse_max_age(cache_control)
                    if ttl is not None:
                        meta["ttl"] = ttl
                self._write_meta(meta_path, meta)
                self.hits += 1
            except (json.JSONDecodeError, OSError):
                pass

    def get_stats(self) -> dict:
        """Trả về thống kê cache."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        total_size = self._get_total_size()
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 1),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self._max_size // (1024 * 1024),
        }

    def clear(self):
        """Xóa toàn bộ cache."""
        with self._lock:
            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            self.hits = 0
            self.misses = 0
            print("[Cache] Đã xóa toàn bộ cache")

    # ──────────────────── Internal ────────────────────

    @staticmethod
    def _hash_url(url: str) -> str:
        """Băm URL thành tên file MD5 (32 ký tự hex)."""
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _write_meta(path: str, meta: dict):
        """Ghi metadata JSON ra file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_expired(meta: dict) -> bool:
        """Kiểm tra cache entry đã hết hạn chưa (dựa trên TTL)."""
        created = meta.get("created_at", 0)
        ttl = meta.get("ttl", 0)
        return time.time() > created + ttl

    @staticmethod
    def _parse_max_age(cache_control: str) -> int | None:
        """
        Parse max-age từ Cache-Control header.
        Ví dụ: "public, max-age=3600" → 3600
        """
        if not cache_control:
            return None
        for directive in cache_control.split(","):
            directive = directive.strip()
            if directive.startswith("max-age="):
                try:
                    return int(directive.split("=", 1)[1])
                except ValueError:
                    return None
        return None

    def _get_total_size(self) -> int:
        """Tính tổng dung lượng thư mục cache (bytes)."""
        total = 0
        try:
            for filename in os.listdir(self._cache_dir):
                filepath = os.path.join(self._cache_dir, filename)
                if os.path.isfile(filepath):
                    total += os.path.getsize(filepath)
        except OSError:
            pass
        return total

    def _evict_if_needed(self):
        """
        Thuật toán LRU Eviction:
        Khi tổng dung lượng cache vượt quá giới hạn, xóa các entry
        ít được truy cập gần đây nhất cho đến khi dung lượng dưới ngưỡng.
        """
        total_size = self._get_total_size()
        if total_size <= self._max_size:
            return

        print(f"[Cache] Dung lượng {total_size // (1024*1024)}MB "
              f"vượt giới hạn {self._max_size // (1024*1024)}MB — bắt đầu eviction")

        # Thu thập tất cả meta entries
        entries = []
        for filename in os.listdir(self._cache_dir):
            if filename.endswith(".meta"):
                meta_path = os.path.join(self._cache_dir, filename)
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    entries.append(meta)
                except (json.JSONDecodeError, OSError):
                    # File meta lỗi → xóa luôn
                    cache_hash = filename.replace(".meta", "")
                    self._remove_cache_entry(cache_hash)

        # Sắp xếp theo last_accessed tăng dần (ít dùng nhất lên đầu)
        entries.sort(key=lambda e: e.get("last_accessed", 0))

        # Xóa cho đến khi dung lượng dưới 90% giới hạn
        target_size = int(self._max_size * 0.9)
        for entry in entries:
            if total_size <= target_size:
                break
            cache_hash = entry.get("hash", "")
            entry_size = entry.get("size", 0)
            self._remove_cache_entry(cache_hash)
            total_size -= entry_size
            print(f"[Cache] Evicted: {entry.get('url', 'unknown')} "
                  f"({entry_size // 1024}KB)")

    def _remove_cache_entry(self, cache_hash: str):
        """Xóa 1 cache entry (cả .data và .meta)."""
        for ext in (".data", ".meta"):
            filepath = os.path.join(self._cache_dir, f"{cache_hash}{ext}")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError:
                pass
