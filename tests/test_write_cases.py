# -*- coding: utf-8 -*-
import sys, os, json, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from write_cases import sanitize_title, validate_cases, dedupe_title, write_all, HEADER

def main():
    assert sanitize_title(' 登录模块:测试*V2 ') == "登录模块测试V2"
    assert len(sanitize_title("长"*80)) <= 50
    good = [["", "登录", "P0", "正常登录", "账号存在", "1.输入 2.点击", "进入首页"],
            ["TC-099", "登录", "P1", "锁定提示", "已锁定", "1.再试", "提示锁定"]]
    v = validate_cases(good)
    assert [r[0] for r in v] == ["TC-001", "TC-002"]        # 重排编号
    for bad, why in [([["", "m", "P3", "t", "p", "s", "e"]], "priority"),
                     ([["", "m", "P0", "", "p", "s", "e"]], "empty title"),
                     ([["", "m", "P0", "t", "p", "s"]], "7 cols")]:
        try: validate_cases(bad); assert False, why
        except ValueError: pass
    assert dedupe_title("登录", ["登录"]) == "登录-2"
    assert dedupe_title("登录", ["登录", "登录-2"]) == "登录-3"
    # 端到端（真实表，PROBE_ 前缀，测完删）
    from feishu_api import get_token, delete_sheet, read_values, get_metainfo
    ST = "ARSnsZ8LAhCDo3tiZp4cLBjwnSf"
    tmp = tempfile.mktemp(suffix=".json")
    json.dump({"title": "PROBE写入校验", "cases": good}, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    t = get_token()
    try:
        r = write_all(tmp, ST, None)
        assert r["total"] == 2 and r["p0"] == 1 and r["p1"] == 1 and r["p2"] == 0
        assert r["title"] == "PROBE写入校验"
        back = read_values(ST, r["sheet_id"], "A1:G%d" % (2 + 2), t)
        assert back[0] == HEADER, back[0]                    # 表头逐格
        assert back[1][0] == "TC-001" and back[2][0] == "TC-002"
        r2 = write_all(tmp, ST, None)                        # 重名 → -2
        assert r2["title"] == "PROBE写入校验-2"
        delete_sheet(ST, r2["sheet_id"], t)
    finally:
        meta = {s["title"]: s["sheetId"] for s in get_metainfo(ST, t)}
        if "PROBE写入校验" in meta: delete_sheet(ST, meta["PROBE写入校验"], t)
        os.path.exists(tmp) and os.remove(tmp)
    s1 = read_values(ST, [s for s in get_metainfo(ST, t) if s["title"] == "Sheet1"][0]["sheetId"], "A1:G2", t)
    assert s1[0] == HEADER or all(v in ("", None) for v in s1[0]), s1  # Sheet1 未被破坏
    print("ALL PASS")

if __name__ == "__main__":
    main()
