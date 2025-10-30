import unittest
from urllib.parse import urlparse, parse_qs


def parse_queue_url(url: str):
    """解析队列 URL，返回包含 host, robot_id, token 的字典；不接受 JSON 包装或非 URL 文本。

    期望格式: https://<HOST>/queue/robots/{robot_id}?t={token}
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("invalid url")

    parts = parsed.path.strip("/").split("/")
    if len(parts) != 3 or parts[0] != "queue" or parts[1] != "robots":
        raise ValueError("invalid path")

    robot_id = parts[2]
    qs = parse_qs(parsed.query)
    token_list = qs.get("t") or qs.get("token")
    if not token_list:
        raise ValueError("missing token")

    token = token_list[0]
    return {"host": parsed.netloc, "robot_id": robot_id, "token": token, "url": url}


class TestQueueURLParsing(unittest.TestCase):
    def test_parse_valid_queue_url(self):
        url = "https://console.example.com/queue/robots/robot-123?t=abc.def.ghi"
        r = parse_queue_url(url)
        self.assertEqual(r["host"], "console.example.com")
        self.assertEqual(r["robot_id"], "robot-123")
        self.assertEqual(r["token"], "abc.def.ghi")

    def test_invalid_missing_token(self):
        url = "https://console.example.com/queue/robots/robot-123"
        with self.assertRaises(ValueError):
            parse_queue_url(url)

    def test_invalid_path(self):
        url = "https://console.example.com/other/robots/robot-123?t=tok"
        with self.assertRaises(ValueError):
            parse_queue_url(url)

    def test_reject_json_in_qr(self):
        # QR 内容应为纯 URL，而非 JSON 包装
        text = '{"url":"https://console.example.com/queue/robots/robot-123?t=tok"}'
        with self.assertRaises(ValueError):
            parse_queue_url(text)


if __name__ == "__main__":
    unittest.main()
