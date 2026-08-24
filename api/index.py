import hashlib
import json
from http.server import BaseHTTPRequestHandler
import urllib.request

# ==================== 核心配置 ====================
# 1. 软件秘钥（必须与你的 EXE 本地软件保持完全一致！）
APP_SECRET_KEY = "MyAwesomeApp2026Key"

# 2. 卡密暗号秘钥（自定义一串英文，必须与本地生成卡密的 Python 脚本保持一致！）
CARD_SECRET_KEY = "MyCardSecret2026"

# 3. Upstash 数据库参数（替换为你自己的真实地址和 Token）
UPSTASH_URL = "https://charming-lynx-124694.upstash.io"
UPSTASH_TOKEN = "gQAAAAAAAecWAAIgcDIyMDg5ZTNhYjBmOGY0NjcyOTM3ZmI4OTQzMWY1ZmQwMg"  # 替换为你的真实 Token
# ==================================================


def is_valid_card_format(card_id):
    """【暗号防伪】校验卡密是否由官方算法生成"""
    # 格式必须刚好为 16 位字母数字
    if len(card_id) != 16 or not card_id.isalnum():
        return False

    prefix = card_id[:12]  # 前 12 位为随机码
    tail = card_id[12:]  # 后 4 位为暗号校验尾号

    # 用前 12 位 + 暗号秘钥 计算官方尾号
    expected_tail = (
        hashlib.md5(f"{prefix}-{CARD_SECRET_KEY}".encode()).hexdigest()[:4].upper()
    )

    return tail == expected_tail


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

        # 情况 1：卡密已被使用过
        if status:
            if status == machine_code:
                return True, "已绑定此电脑"
            else:
                return (
                    False,
                    "卡密已被其他电脑激活使用，无法重复激活！",
                )

        # 情况 2：合法卡密首次激活 -> 写入数据库锁定绑定此机器码
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
        content_length = int(self.headers.get("Content-Length", 0))
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

            # 【防伪第一关】校验暗号，非官方计算生成的卡密直接弹回！
            if not is_valid_card_format(card_id):
                self._send_response(
                    400,
                    {
                        "error": "无效的卡密！请输入正确的正版授权卡密。"
                    },
                )
                return

            # 【绑定第二关】查询并核销卡密
            valid, msg = verify_and_bind_card(card_id, machine_code)
            if not valid:
                self._send_response(400, {"error": msg})
                return

            # 算出 16 位专属激活码（由机器码 + 私钥加密生成）
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
