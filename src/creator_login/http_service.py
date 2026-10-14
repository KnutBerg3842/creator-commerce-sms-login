from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .infrai_sms import InfraiError, InfraiSms
from .models import CodeRequest, CodeVerification
from .workflow import CreatorLoginService


class CreatorLoginHandler(BaseHTTPRequestHandler):
    service: CreatorLoginService

    def do_POST(self) -> None:
        try:
            body = self._read_json()
            if self.path == "/login/code":
                result: Any = self.service.request_code(CodeRequest.from_json(body))
            elif self.path == "/login/verify":
                result = self.service.verify_code(CodeVerification.from_json(body)).to_dict()
            else:
                self._send(404, {"error": "route not found"})
                return
            self._send(200, result)
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except InfraiError as exc:
            client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            self._send(client_status, {"error": exc.code, "detail": exc.detail})
        except (ConnectionError, RuntimeError, json.JSONDecodeError) as exc:
            self._send(502, {"error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request body must be an object")
        return value

    def _send(self, status: int, body: Any) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    CreatorLoginHandler.service = CreatorLoginService(InfraiSms())
    server = ThreadingHTTPServer(("127.0.0.1", port), CreatorLoginHandler)
    print(f"creator login service listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
