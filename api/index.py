"""
Vercel Serverless Entrypoint for MoveSync Rating Intelligence API.
"""

import os
import sys
from urllib.parse import parse_qs, urlencode

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app import app


class VercelPathRewriteMiddleware:
    """
    Middleware to adapt Vercel serverless rewrites.
    When Vercel rewrites /api/:path* to /api/index.py, it passes :path* in the query string as ?path=...
    This middleware reconstructs the intended /api/:path ASGI scope path while preserving all other query parameters.
    """
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path in ("/api/index.py", "/api/index", "/index.py"):
                query_string = scope.get("query_string", b"").decode("utf-8")
                if query_string:
                    params = parse_qs(query_string, keep_blank_values=True)
                    if "path" in params:
                        subpath = params.pop("path", [""])[0].strip("/")
                        new_path = f"/api/{subpath}" if subpath else "/api"
                        scope["path"] = new_path
                        scope["raw_path"] = new_path.encode("utf-8")
                        scope["query_string"] = urlencode(params, doseq=True).encode("utf-8")
        await self.asgi_app(scope, receive, send)


# Wrap FastAPI app for Vercel serverless execution
app = VercelPathRewriteMiddleware(app)
