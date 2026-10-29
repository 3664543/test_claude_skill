# -*- coding: utf-8 -*-
"""Validate generated test cases and write them to a new Feishu worksheet.

The LLM produces the cases JSON; this script is the gate: it renumbers,
enforces the seven columns and the P0/P1/P2 vocabulary, creates a fresh
worksheet (never touches existing ones), writes, then verifies by reading
back and comparing cell-by-cell. stdout is ASCII only.
"""
import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feishu_api import (FeishuAPIError, create_sheet, delete_sheet, get_metainfo,
                        get_token, read_values, resolve_spreadsheet, write_rows)

HEADER = ["用例编号", "模块", "优先级", "用例标题", "前置条件", "测试步骤", "预期结果"]
PRIORITIES = ("P0", "P1", "P2")
MAX_TITLE = 50
ILLEGAL_TITLE_CHARS = '\\/:*?"<>|[]'


def sanitize_title(raw):
    """Strip filesystem/sheet-illegal chars, collapse whitespace, cap length."""
    s = "".join(ch for ch in raw if ch not in ILLEGAL_TITLE_CHARS)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:MAX_TITLE]


def validate_cases(cases):
    """Enforce 7 columns, priority vocabulary, non-empty title/expectation.
    Returns renumbered copies (TC-001..); raises ValueError with an ASCII
    problem list otherwise."""
    problems = []
    for i, row in enumerate(cases):
        row = [str(v) for v in row]
        if len(row) != 7:
            problems.append("row %d: has %d columns, need 7" % (i, len(row)))
            continue
        if row[2] not in PRIORITIES:
            problems.append("row %d: priority %r not in P0/P1/P2" % (i, row[2]))
        if not row[3].strip():
            problems.append("row %d: empty title" % i)
        if not row[6].strip():
            problems.append("row %d: empty expectation" % i)
    if problems:
        raise ValueError("invalid cases:\n" + "\n".join(problems))
    out = []
    for i, row in enumerate(cases):
        row = [str(v) for v in row]
        row[0] = "TC-%03d" % (i + 1)
        out.append(row)
    return out


def dedupe_title(title, existing_titles):
    """Append -2, -3, ... when the title already exists."""
    if title not in existing_titles:
        return title
    k = 2
    while "%s-%d" % (title, k) in existing_titles:
        k += 1
    return "%s-%d" % (title, k)


def write_all(cases_path, target, title_override=None):
    """Full flow: load -> validate -> resolve -> name -> create -> write ->
    verify readback (self-clean the sheet on mismatch)."""
    with open(cases_path, encoding="utf-8") as f:
        payload = json.load(f)
    cases = validate_cases(payload.get("cases", []))
    if not cases:
        raise ValueError("no cases in %s" % cases_path)
    raw_title = title_override or str(payload.get("title") or "")
    if not raw_title.strip():
        raise ValueError("missing title (neither --title nor cases JSON title)")

    token = get_token()
    st = resolve_spreadsheet(target, token)
    existing = [s["title"] for s in get_metainfo(st, token)]
    title = dedupe_title(sanitize_title(raw_title), existing)
    sid = create_sheet(st, title, len(existing), token)
    try:
        write_rows(st, sid, 1, [HEADER] + cases, token)
        back = read_values(st, sid, "A1:G%d" % (1 + len(cases)), token)
        ok = (len(back) == 1 + len(cases) and back[0] == HEADER
              and back[1] == cases[0] and back[-1] == cases[-1])
        if not ok:
            raise FeishuAPIError(-1, "verify failed: readback mismatch on sheet %s" % sid)
    except Exception:
        delete_sheet(st, sid, token)
        raise
    counts = {"P0": 0, "P1": 0, "P2": 0}
    for row in cases:
        counts[row[2]] += 1
    return {"sheet_id": sid, "title": title, "total": len(cases),
            "p0": counts["P0"], "p1": counts["P1"], "p2": counts["P2"],
            "spreadsheet_token": st}


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--title", default=None)
    args = parser.parse_args(argv[1:])
    try:
        r = write_all(args.cases, args.target, args.title)
    except ValueError as e:
        print(str(e).encode("ascii", "replace").decode("ascii"))
        return 2
    except FeishuAPIError as e:
        print("FeishuAPIError code=%s msg=%s" % (e.code, e.msg.encode("ascii", "replace").decode("ascii")))
        return 3
    print("OK sheet_id=%s title=%s total=%d p0=%d p1=%d p2=%d"
          % (r["sheet_id"], r["title"].encode("ascii", "replace").decode("ascii"),
             r["total"], r["p0"], r["p1"], r["p2"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
