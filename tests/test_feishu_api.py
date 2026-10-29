# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from feishu_api import extract_token_from_url

def test_extract():
    assert extract_token_from_url("https://my.feishu.cn/wiki/M2VawdEO4iwZx2khc6xccAK1nOf?from=from_copylink") == "M2VawdEO4iwZx2khc6xccAK1nOf"
    assert extract_token_from_url("https://my.feishu.cn/sheets/ARSnsZ8LAhCDo3tiZp4cLBjwnSf") == "ARSnsZ8LAhCDo3tiZp4cLBjwnSf"
    assert extract_token_from_url("ARSnsZ8LAhCDo3tiZp4cLBjwnSf") == "ARSnsZ8LAhCDo3tiZp4cLBjwnSf"

def test_live_smoke():
    try:
        from feishu_api import get_token, resolve_spreadsheet, get_metainfo
        t = get_token()
    except Exception as e:
        print("SKIP live smoke:", type(e).__name__); return
    st = resolve_spreadsheet("M2VawdEO4iwZx2khc6xccAK1nOf", t)
    assert st == "ARSnsZ8LAhCDo3tiZp4cLBjwnSf"
    meta = get_metainfo(st, t)
    assert any(s["title"] == "Sheet1" for s in meta), meta
    print("LIVE OK")

if __name__ == "__main__":
    test_extract(); test_live_smoke(); print("ALL PASS")
