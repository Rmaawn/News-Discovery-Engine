"""
server.py
=========

راه‌اندازی سرور WSGI برای داشبورد.

ترتیب انتخاب سرور:
1. ``waitress`` (سبک، پایدار و مناسب Production) در صورت نصب بودن.
2. در غیر این‌صورت، سرور توسعه‌ی داخلی Flask (فقط برای محیط توسعه).

پورت از متغیر محیطی ``PORT`` خوانده می‌شود (پیش‌فرض ۳۰۰۰) تا با پلتفرم
Liara سازگار باشد.
"""

from __future__ import annotations

import os

from .app import app


def _resolve_port(default: int = 3000) -> int:
    try:
        return int(os.getenv("PORT", default))
    except (TypeError, ValueError):
        return default


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    """اجرای سرور داشبورد (Blocking)."""
    initial_port = port or _resolve_port()
    ports_to_try = [initial_port] + [p for p in [3001, 3002, 5000, 8080] if p != initial_port]

    for p in ports_to_try:
        try:
            from waitress import serve as waitress_serve
            print(f"[dashboard] serving with waitress on http://{host}:{p}")
            waitress_serve(app, host=host, port=p, threads=6)
            break
        except OSError as e:
            if getattr(e, 'errno', None) == 98 or "Address already in use" in str(e):
                print(f"[dashboard] Port {p} is in use, trying next port...")
                continue
            raise
        except ImportError:
            print(f"[dashboard] waitress not found, using Flask dev server on http://{host}:{p}")
            app.run(host=host, port=p, threaded=True)
            break


if __name__ == "__main__":
    serve()
