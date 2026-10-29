# -*- coding: utf-8 -*-
"""Feishu Open API client (stdlib only).

All requests are made from Python with UTF-8 JSON bodies: the Windows
command line mangles Chinese arguments, so nothing Chinese ever passes
through a shell. stdout stays ASCII on purpose.
"""
import json
import os
import re
import socket
import urllib.error
import urllib.request

BASE = "https://open.feishu.cn/open-apis"
APP_ID_ENV = "FEISHU_APP_ID"
APP_SECRET_ENV = "FEISHU_APP_SECRET"


class FeishuAPIError(Exception):
    """Feishu API returned an error (non-zero code or HTTP error)."""

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        super().__init__("FeishuAPIError code=%s msg=%s" % (code, msg))


def get_token(app_id=None, app_secret=None):
    """Fetch tenant_access_token. Credentials default to env vars."""
    app_id = app_id or os.environ.get(APP_ID_ENV)
    app_secret = app_secret or os.environ.get(APP_SECRET_ENV)
    if not app_id or not app_secret:
        raise FeishuAPIError(-1, "missing %s / %s env vars; set them in "
                             "~/.claude/settings.json" % (APP_ID_ENV, APP_SECRET_ENV))
    out = api("POST", "/auth/v3/tenant_access_token/internal",
              {"app_id": app_id, "app_secret": app_secret})
    return out["tenant_access_token"]


def api(method, path, body=None, token=None):
    """Call an Open API endpoint; raise FeishuAPIError on any error."""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            out = json.loads(raw)
        except ValueError:
            raise FeishuAPIError(e.code, raw[:300].encode("ascii", "replace").decode("ascii"))
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise FeishuAPIError(-1, "network error: %s"
                             % str(e).encode("ascii", "replace").decode("ascii"))
    if out.get("code", 0) != 0:
        raise FeishuAPIError(out.get("code"), out.get("msg", ""))
    return out


def extract_token_from_url(target):
    """Accept a wiki URL, a sheets URL, or a bare token."""
    target = target.strip()
    m = re.search(r"(?:wiki|sheets)/([A-Za-z0-9]+)", target)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", target):
        return target
    raise FeishuAPIError(-1, "cannot extract token from target")


def resolve_spreadsheet(target, token):
    """Resolve a wiki URL/token / sheets URL / bare token to a spreadsheet token.
    Bare tokens are ambiguous: try the wiki node first, fall back to treating
    the value as a spreadsheet token when it resolves as neither a wiki node
    nor a sheet URL."""
    t = extract_token_from_url(target)
    if "/sheets/" in target:
        return t
    try:
        node = api("GET", "/wiki/v2/spaces/get_node?token=" + t, token=token)
    except FeishuAPIError:
        if "/wiki/" in target:
            raise
        return t  # bare token that is not a wiki node -> spreadsheet token
    info = node["data"]["node"]
    if info.get("obj_type") != "sheet":
        raise FeishuAPIError(-1, "wiki node obj_type=%r is not 'sheet'" % info.get("obj_type"))
    return info["obj_token"]


def get_metainfo(spreadsheet_token, token):
    """Return [{'sheetId','title','rowCount','columnCount'}, ...]."""
    out = api("GET", "/sheets/v2/spreadsheets/%s/metainfo" % spreadsheet_token, token=token)
    sheets = out["data"]["sheets"]
    return [{"sheetId": s["sheetId"], "title": s["title"],
             "rowCount": int(s["rowCount"]), "columnCount": int(s["columnCount"])}
            for s in sheets]


def create_sheet(spreadsheet_token, title, index, token):
    """Create a worksheet (v3). NOTE: 'title' must be TOP-LEVEL in the body —
    nested inside 'sheet' it is silently ignored and Feishu auto-names SheetN."""
    out = api("POST", "/sheets/v3/spreadsheets/%s/sheets" % spreadsheet_token,
              {"title": title, "index": index}, token=token)
    return out["data"]["sheet"]["sheet_id"]


def delete_sheet(spreadsheet_token, sheet_id, token):
    api("DELETE", "/sheets/v3/spreadsheets/%s/sheets/%s" % (spreadsheet_token, sheet_id),
        token=token)


def read_values(spreadsheet_token, sheet_id, rng, token):
    """Read a range like 'A1:G5' with ToString rendering; pad short rows to
    the range's column count, null -> ''."""
    out = api("GET", "/sheets/v2/spreadsheets/%s/values/%s!%s?valueRenderOption=ToString"
              % (spreadsheet_token, sheet_id, rng), token=token)
    m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", rng)
    ncols = _col_index(m.group(3)) - _col_index(m.group(1)) + 1
    values = out["data"]["valueRange"].get("values", [])
    rows = []
    for r in values:
        r = ["" if v is None else v for v in r]
        if len(r) < ncols:
            r = r + [""] * (ncols - len(r))
        rows.append(r)
    return rows


def _col_index(letters):
    """'A' -> 0 based index used for width math."""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def write_rows(spreadsheet_token, sheet_id, start_row, rows, token):
    """Fixed-position write of `rows` (list of 7-col lists) starting at
    1-based start_row, columns A..G. Feishu auto-extends the grid when the
    write goes past the current row count (verified empirically 200->250);
    values_append is banned: it skips previously-cleared rows and leaves gaps."""
    rng = "A%d:G%d" % (start_row, start_row + len(rows) - 1)
    return api("PUT", "/sheets/v2/spreadsheets/%s/values" % spreadsheet_token,
               {"valueRange": {"range": "%s!%s" % (sheet_id, rng),
                               "values": [[str(v) for v in r[:7]] for r in rows]}},
               token=token)


def find_last_nonempty_row(spreadsheet_token, sheet_id, token):
    """1-based last row with any non-empty cell in A..G; 0 when empty."""
    meta = {s["sheetId"]: s for s in get_metainfo(spreadsheet_token, token)}[sheet_id]
    rows = read_values(spreadsheet_token, sheet_id, "A1:G%d" % meta["rowCount"], token)
    last = 0
    for i, r in enumerate(rows):
        if any(v not in ("", None) for v in r):
            last = i + 1
    return last
