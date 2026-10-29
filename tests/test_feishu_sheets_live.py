# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from feishu_api import (get_token, create_sheet, delete_sheet, read_values,
                        write_rows, find_last_nonempty_row, get_metainfo)
ST = "ARSnsZ8LAhCDo3tiZp4cLBjwnSf"

def main():
    t = get_token()
    sid = create_sheet(ST, "PROBE_plan_temp", 1, t)
    try:
        meta = {s["title"]: s for s in get_metainfo(ST, t)}
        assert "PROBE_plan_temp" in meta, meta.keys()          # v3 title 顶层生效
        assert meta["PROBE_plan_temp"]["sheetId"] == sid
        rows = [["TC-001", "登录", "P0", "正常登录", "账号存在", "1.输入 2.点登录", "进入首页"],
                ["TC-002", "登录", "P1", "密码错误提示", "账号存在", "1.输错密码", "提示错误"]]
        write_rows(ST, sid, 1, rows, t)                         # 首行直接写
        back = read_values(ST, sid, "A1:G2", t)
        assert back[0][0] == "TC-001" and back[0][2] == "P0", back
        assert back[1][3] == "密码错误提示", back               # 中文逐格比对
        assert find_last_nonempty_row(ST, sid, t) == 2
        write_rows(ST, sid, 3, [["TC-003", "m", "P2", "t", "p", "s", "e"]], t)
        assert find_last_nonempty_row(ST, sid, t) == 3
        # 超出默认 200 行写入（自动扩容验证）
        write_rows(ST, sid, 250, [["TC-250", "m", "P2", "t", "p", "s", "e"]], t)
        assert read_values(ST, sid, "A250:G250", t)[0][0] == "TC-250"
    finally:
        delete_sheet(ST, sid, t)
        titles = [s["title"] for s in get_metainfo(ST, t)]
        assert "PROBE_plan_temp" not in titles
    print("ALL PASS")

if __name__ == "__main__":
    main()
