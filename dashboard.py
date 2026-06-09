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


def create_app(proxy_logger, cache_manager, web_filter):
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
            "simulate_failover": config.SIMULATE_FAILOVER
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
        if "simulate_failover" in data:
            config.SIMULATE_FAILOVER = bool(data["simulate_failover"])
        return jsonify({
            "status": "ok",
            "bandwidth_limit": config.BANDWIDTH_LIMIT,
            "simulate_failover": config.SIMULATE_FAILOVER
        })

    return app
