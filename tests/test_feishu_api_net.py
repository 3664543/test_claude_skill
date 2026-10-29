# -*- coding: utf-8 -*-
"""Network failures must surface as FeishuAPIError (machine-readable, exit 3
per SKILL.md), never as a raw URLError/timeout traceback."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import feishu_api
from feishu_api import FeishuAPIError, api


def main():
    original = feishu_api.BASE
    feishu_api.BASE = "https://127.0.0.1:9/open-apis"  # discard port: refused fast
    try:
        try:
            api("GET", "/auth/v3/tenant_access_token/internal",
                {"app_id": "x", "app_secret": "y"})
            raise AssertionError("expected FeishuAPIError")
        except FeishuAPIError as e:
            assert "network error" in e.msg.lower(), e.msg
    finally:
        feishu_api.BASE = original
    print("ALL PASS")

if __name__ == "__main__":
    main()
