import hashlib
import json
from http.server import BaseHTTPRequestHandler
import urllib.request

# 1. 软件密钥（与你 Python 软件里的密钥保持一致）
APP_SECRET_KEY = "MyAwesomeApp2026Key"

# 2. 填入你在 Upstash 获得的 REST URL 和 TOKEN
UPSTASH_REDIS_REST_URL="https://charming-lynx-124694.upstash.io"  # 替换为你的 REST URL
UPSTASH_REDIS_REST_TOKEN="********"  # 替换为你的 REST TOKEN


def verify_and_bind_card(card_id, machine_code):
    """查询并绑定卡密"""
    url = f"{UPSTASH_URL}/get/{card_id}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            status = res_data.get("result")

        # 情况 1：卡密已被使用
        if status:
            if status == machine_code:
                return True, "已绑定此电脑"
            else:
                return (
                    False,
                    "卡密已被其他电脑激活使用，无法重复激活！",
                )

        # 情况 2：卡密首次激活 -> 写入数据库绑定机器码
        set_url = f"{UPSTASH_URL}/set/{card_id}/{machine_code}"
        set_req = urllib.request.Request(
            set_url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        with urllib.request.urlopen(set_req):
            pass

        return True, "激活成功"

    except Exception as e:
        return False, f"数据库连接异常: {str(e)}"


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode("utf-8"))
            card_id = data.get("card_id", "").strip().upper()
            machine_code = data.get("machine_code", "").strip().upper()

            if not card_id or not machine_code:
                self._send_response(
                    400, {"error": "卡密与机器码均不能为空！"}
                )
                return

            if len(card_id) < 6:
                self._send_response(
                    400, {"error": "卡密格式不正确，请检查！"}
                )
                return

            valid, msg = verify_and_bind_card(card_id, machine_code)
            if not valid:
                self._send_response(400, {"error": msg})
                return

            # 计算生成 16 位激活码
            license_key = (
                hashlib.md5(f"{machine_code}-{APP_SECRET_KEY}".encode())
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
