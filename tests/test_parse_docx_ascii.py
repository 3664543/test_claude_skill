# -*- coding: utf-8 -*-
"""parse_docx CLI stdout must be pure ASCII even for Chinese paths (Review
Focus 1: GBK console mangling of Chinese stdout poisons the orchestrator)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "parse_docx.py")


def main():
    docx = os.path.join(HERE, "_out", "sample_req.docx")
    out_dir = os.path.join(tempfile.gettempdir(), "测试目录_中文", "用例输出")
    p = subprocess.run([sys.executable, SCRIPT, docx, out_dir],
                       capture_output=True, timeout=120)
    out = p.stdout.decode("utf-8", errors="replace")
    assert p.returncode == 0, (p.returncode, out, p.stderr.decode("utf-8", "replace"))
    non_ascii = [c for c in out if ord(c) > 127]
    assert not non_ascii, "non-ASCII stdout: %r" % ("".join(non_ascii)[:80],)
    assert out.startswith("PARSED "), out
    print("ALL PASS")

if __name__ == "__main__":
    main()
