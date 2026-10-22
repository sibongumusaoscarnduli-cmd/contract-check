"""Synthetic local fixture API for ContractCheck examples."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FixtureHandler(BaseHTTPRequestHandler):
    server_version = "ContractCheckFixture/1.0"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        elif self.path.startswith("/orders/"):
            order_id = self.path.rsplit("/", 1)[-1]
            self._send(200, {"id": order_id, "status": "pending", "total": 12.5})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/orders":
            self._send(404, {"error": "not found"})
            return
        size = int(self.headers.get("Content-Length", "0"))
        if size > 100_000:
            self._send(413, {"error": "payload too large"})
            return
        try:
            order = json.loads(self.rfile.read(size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, {"error": "invalid JSON"})
            return
        if not isinstance(order, dict) or not order.get("customer") or not order.get("items"):
            self._send(400, {"error": "customer and items are required"})
            return
        total = sum(float(item.get("unit_price", 12.5)) * int(item.get("quantity", 1)) for item in order["items"])
        self._send(201, {"id": "sample-order", "status": "pending", "total": total})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve ContractCheck's synthetic local orders API.")
    parser.add_argument("--port", type=int, default=8070)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), FixtureHandler)
    print(f"Synthetic fixture API listening at http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping fixture API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
