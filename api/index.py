import hashlib
import json
from http.server import BaseHTTPRequestHandler

# 【必须和你软件里的 SECRET_KEY 完全一模一样】
SECRET_KEY = "MyAwesomeApp2026Key"


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode("utf-8"))
            machine_code = data.get("machine_code", "").strip().upper()

            if not machine_code:
                self._send_response(
                    400, {"error": "机器码不能为空！"}
                )
                return

            # 计算激活码
            license_key = (
                hashlib.md5(f"{machine_code}-{SECRET_KEY}".encode())
                .hexdigest()[:16]
                .upper()
            )

            self._send_response(200, {"license_key": license_key})
        except Exception as e:
            self._send_response(500, {"error": str(e)})

    def _send_response(self, code, response_data):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        self.end_headers()