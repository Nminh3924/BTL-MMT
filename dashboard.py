"""
dashboard.py — Real-time Dashboard cho Proxy Server (Flask).

Cung cấp giao diện web tại http://localhost:5000 để:
- Xem lịch sử request (URL, Method, Status Code, Cache Status).
- Biểu đồ tỷ lệ Cache Hit vs Cache Miss.
- Thống kê tổng request, bandwidth tiết kiệm, domain bị chặn.
- Top 10 domain truy cập nhiều nhất.

Chạy trong thread riêng từ proxy.py, không cần khởi động riêng.
"""

import os

from flask import Flask, render_template, jsonify

import config


def create_app(proxy_logger, cache_manager, web_filter, rate_limiter=None):
    """
    Factory function tạo Flask app.
    Nhận các module từ proxy.py để truy cập dữ liệu thời gian thực.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
    )

    # Tắt log Flask để không làm rối terminal của proxy
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    @app.route("/")
    def index():
        """Trang chủ Dashboard."""
        return render_template("dashboard.html")

    @app.route("/api/stats")
    def api_stats():
        """API trả về thống kê tổng hợp (JSON)."""
        stats = proxy_logger.get_stats()
        cache_stats = cache_manager.get_stats()
        stats["cache_size_mb"] = cache_stats["total_size_mb"]
        stats["cache_max_mb"] = cache_stats["max_size_mb"]
        if rate_limiter:
            stats["rate_limit_stats"] = rate_limiter.get_stats()
        return jsonify(stats)

    @app.route("/api/logs")
    def api_logs():
        """API trả về log entries gần nhất (JSON)."""
        logs = proxy_logger.get_recent_logs(100)
        return jsonify(logs)

    @app.route("/api/cache/clear", methods=["POST"])
    def api_clear_cache():
        """API xóa toàn bộ cache."""
        cache_manager.clear()
        return jsonify({"status": "ok", "message": "Cache đã được xóa"})

    @app.route("/api/filter/reload", methods=["POST"])
    def api_reload_filter():
        """API tải lại danh sách blacklist/adlist."""
        web_filter.reload()
        return jsonify({"status": "ok", "message": "Đã tải lại bộ lọc"})

    @app.route("/api/settings", methods=["GET"])
    def api_get_settings():
        """API lấy cấu hình hiện tại."""
        return jsonify({
            "bandwidth_limit": config.BANDWIDTH_LIMIT,
            "simulate_http_error": config.SIMULATE_HTTP_ERROR,
            "simulate_http_error_code": config.SIMULATE_HTTP_ERROR_CODE,
            "auth_enabled": config.AUTH_ENABLED,
            "auth_username": config.AUTH_USERNAME,
            "rate_limit_max_requests": config.RATE_LIMIT_MAX_REQUESTS,
            "rate_limit_window": config.RATE_LIMIT_WINDOW,
        })

    @app.route("/api/settings", methods=["POST"])
    def api_post_settings():
        """API cập nhật cấu hình."""
        from flask import request
        data = request.json or {}
        if "bandwidth_limit" in data:
            try:
                config.BANDWIDTH_LIMIT = int(data["bandwidth_limit"])
            except ValueError:
                pass
        if "simulate_http_error" in data:
            config.SIMULATE_HTTP_ERROR = bool(data["simulate_http_error"])
        if "simulate_http_error_code" in data:
            try:
                config.SIMULATE_HTTP_ERROR_CODE = int(data["simulate_http_error_code"])
            except ValueError:
                pass
        if "auth_enabled" in data:
            config.AUTH_ENABLED = bool(data["auth_enabled"])
        if "auth_username" in data:
            config.AUTH_USERNAME = str(data["auth_username"])
        if "auth_password" in data:
            val = str(data["auth_password"])
            if val:  # Chỉ cập nhật nếu không rỗng
                config.AUTH_PASSWORD = val
        if "rate_limit_max_requests" in data:
            try:
                config.RATE_LIMIT_MAX_REQUESTS = int(data["rate_limit_max_requests"])
            except ValueError:
                pass
        if "rate_limit_window" in data:
            try:
                config.RATE_LIMIT_WINDOW = int(data["rate_limit_window"])
            except ValueError:
                pass
        return jsonify({
            "status": "ok",
            "bandwidth_limit": config.BANDWIDTH_LIMIT,
            "simulate_http_error": config.SIMULATE_HTTP_ERROR,
            "simulate_http_error_code": config.SIMULATE_HTTP_ERROR_CODE,
            "auth_enabled": config.AUTH_ENABLED,
            "rate_limit_max_requests": config.RATE_LIMIT_MAX_REQUESTS,
            "rate_limit_window": config.RATE_LIMIT_WINDOW,
        })

    return app
