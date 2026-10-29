# -*- coding: utf-8 -*-
import io, os, re, sys
SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")

def main():
    md = io.open(SKILL, encoding="utf-8").read()
    rules = io.open(r"E:/Python/claude_test/claude.txt", encoding="utf-8").read()
    lines = [l.strip() for l in rules.strip().splitlines() if l.strip()]
    missing = [l for l in lines if l not in md]
    assert not missing, missing                    # claude.txt 每一行都逐字在 SKILL.md 中
    assert "M2VawdEO4iwZx2khc6xccAK1nOf" in md     # 默认目标
    assert "parse_docx.py" in md and "write_cases.py" in md
    print("ALL PASS")

if __name__ == "__main__":
    main()
