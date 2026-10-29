# -*- coding: utf-8 -*-
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from make_fixture import build_fixture
from parse_docx import extract

def main():
    out = os.path.join(HERE, "_out")
    docx = build_fixture(os.path.join(out, "sample_req.docx"))
    r = extract(docx, out)
    assert any("示例登录需求" == p["text"] for p in r["paragraphs"]), r["paragraphs"]
    assert any("验证码登录" in c for tbl in r["tables"] for row in tbl for c in row)
    assert any("验收标准" in tb for tb in r["textboxes"]), r["textboxes"]
    assert r["textboxes"].count("验收标准：登录耗时小于2秒") == 1, r["textboxes"]
    assert r["textboxes"].count("验收标准二：验证码发送耗时小于10秒") == 1, r["textboxes"]
    assert len(r["images"]) == 1 and os.path.isfile(r["images"][0])
    saved = json.load(open(os.path.join(out, "content.json"), encoding="utf-8"))
    assert saved["paragraphs"] == r["paragraphs"]
    print("ALL PASS")

if __name__ == "__main__":
    main()
