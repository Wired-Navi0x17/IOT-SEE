"""Laptop-side relay for CricketData when the UNO Q cannot do HTTPS itself (no internet, or its clock is wrong
so certificates look "not yet valid"). Run on the laptop, then expose it to the board over USB:

    python3 tools/api_relay.py            # listens on 127.0.0.1:3129
    adb reverse tcp:3129 tcp:3129         # the board's 127.0.0.1:3129 now reaches the laptop

and start the hub with CRICAPI_BASE=http://127.0.0.1:3129. Only GET /v1/... is forwarded to api.cricapi.com.
"""
import http.server
import urllib.error
import urllib.request

UPSTREAM = "https://api.cricapi.com"


class Relay(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server naming)
        if not self.path.startswith("/v1/"):
            self.send_error(404)
            return
        try:
            with urllib.request.urlopen(UPSTREAM + self.path, timeout=20) as r:
                body, code = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, code = e.read(), e.code
        except OSError as e:
            self.send_error(502, str(e))
            return
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("relay:", self.path.split("apikey=")[0], args[1] if len(args) > 1 else "")


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", 3129), Relay).serve_forever()
