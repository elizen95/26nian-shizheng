#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时政库检索工具：按模块 / 月份 / 关键词查询，返回所在文件与行号。

用法:
  python shizheng.py list
  python shizheng.py stats
  python shizheng.py module -c 06 [--limit 20] [--offset 0]
  python shizheng.py month -m 10
  python shizheng.py search -k 长征 [--limit 10]
  python shizheng.py get -c 06 -t "低空经济"      # 标题精确/前缀匹配
  python shizheng.py outline                      # 全部条目标题（倒序）
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF  = os.path.join(os.path.dirname(HERE), "references")

def load():
    with open(os.path.join(REF, "index.json"), encoding="utf-8") as f:
        idx = json.load(f)
    with open(os.path.join(REF, "textbook.json"), encoding="utf-8") as f:
        tb = json.load(f)
    return idx, tb

def periods_sorted(items):
    order = {}
    i = 100
    for p in sorted({e["period"] for e in items}):
        order[p] = i; i -= 1
    return order

def period_key(period):
    m = re.match(r'2026年(\d{1,2})月(上|下)', period)
    if not m: return (0, 0)
    return (int(m.group(1)), 0 if m.group(2) == "下" else 1)

def sort_desc(items):
    return sorted(items, key=lambda e: (-period_key(e["period"])[0], period_key(e["period"])[1]))

def line_index(path):
    """标题 -> 行号 的索引。"""
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if line.startswith("### "):
                    out.setdefault(line[4:].strip(), n)
    except FileNotFoundError:
        pass
    return out

def cmd_list(a):
    idx, _ = load()
    print(f"时政库 {idx['coverage']} ｜ {idx['module_count']} 个模块 ｜ "
          f"{idx['entry_count']} 条考点 ｜ {idx['question_count']} 道题\n")
    print(f"{'码':<4}{'模块':<28}{'条数':>5}  文件")
    print("-" * 78)
    for m in idx["modules"]:
        print(f"{m['code']:<4}{m['name']:<28}{m['count']:>5}  {m['file']}")

def cmd_stats(a):
    idx, tb = load()
    print(f"覆盖范围 : {idx['coverage']}")
    print(f"模块数   : {idx['module_count']}")
    print(f"考点总数 : {idx['entry_count']}")
    print(f"习题总数 : {idx['question_count']}")
    allitems = [e for m in tb["modules"] for e in m["items"]]
    from collections import Counter
    c = Counter(e["period"] for e in allitems)
    print("\n各期条目数（倒序）:")
    for p in sorted(c, key=lambda x: (-period_key(x)[0], period_key(x)[1])):
        print(f"  {p}: {c[p]}")

def cmd_module(a):
    idx, tb = load()
    code = a.code.zfill(2) if hasattr(a, "code") else ""
    mod = next((m for m in tb["modules"] if m["code"] == code), None)
    if not mod:
        print("模块不存在。可用模块：", ", ".join(m["code"] for m in tb["modules"]))
        return
    fn = next(m["file"] for m in idx["modules"] if m["code"] == code)   # 形如 references/m03-*.md
    li = line_index(os.path.join(os.path.dirname(REF), fn))
    items = sort_desc(mod["items"])
    sel = items[a.offset: a.offset + a.limit] if a.limit else items[a.offset:]
    print(f"# {mod['code']} {mod['name']}  （共 {len(items)} 条，显示 {len(sel)} 条）")
    print(f"# 文件：{fn}\n")
    print("【本模块怎么考】" + mod["intro"] + "\n")
    cur = None
    for e in sel:
        if e["period"] != cur:
            cur = e["period"]
            print(f"\n◆ {cur}")
        ln = li.get(e["title"], "?")
        print(f"  [{e['period']}] {e['title']}   → {fn}:{ln}")
        body = e["body"].strip()
        if body:
            print("      " + body[:400].replace("\n", "\n      "))

def cmd_month(a):
    _, tb = load()
    idx, _ = load()
    mon = int(a.month)
    allitems = [e for m in tb["modules"] for e in m["items"]]
    sel = [e for e in allitems if re.match(r'2026年%d月' % mon, e["period"])]
    if not sel:
        print(f"没有 {mon} 月的条目。可查范围 1—10 月。"); return
    sel = sorted(sel, key=lambda e: (-period_key(e["period"])[0], period_key(e["period"])[1]))
    print(f"# 2026 年 {mon} 月（{len(sel)} 条，按月内倒序：下 → 上）\n")
    cur = None
    for e in sel:
        if e["period"] != cur:
            cur = e["period"]; print(f"\n◆ {cur}")
        print(f"  {e['title']}")

def cmd_search(a):
    idx, tb = load()
    kw = a.keyword
    hits = []
    for m in tb["modules"]:
        fn = next(x["file"] for x in idx["modules"] if x["code"] == m["code"])
        li = None
        for e in m["items"]:
            if kw in e["title"] or kw in e["body"]:
                if li is None:
                    li = line_index(os.path.join(os.path.dirname(REF), fn))
                score = 3 if kw in e["title"] else 1
                hits.append((score, m["code"], m["name"], e, fn, li.get(e["title"])))
    if not hits:
        print(f"未命中「{kw}」。换个更短的词，或试试 list 看模块。"); return
    hits.sort(key=lambda x: (-x[0], -period_key(x[3]["period"])[0]))
    print(f"# 关键词「{kw}」命中 {len(hits)} 条（前 {min(a.limit, len(hits))} 条）\n")
    for score, code, name, e, fn, ln in hits[:a.limit]:
        print(f"[{code} {name}] {e['period']}")
        print(f"   {e['title']}   → {fn}:{ln}")
        body = e["body"].replace("\n", " ")
        pos = body.find(kw)
        seg = body[max(0, pos - 60): pos + 120] if pos >= 0 else body[:180]
        print(f"   …{seg}…")
        print()

def cmd_get(a):
    idx, tb = load()
    code = a.code.zfill(2)
    mod = next((m for m in tb["modules"] if m["code"] == code), None)
    if not mod: print("模块不存在"); return
    fn = next(x["file"] for x in idx["modules"] if x["code"] == code)
    li = line_index(os.path.join(os.path.dirname(REF), fn))
    for e in mod["items"]:
        if e["title"] == a.title or e["title"].startswith(a.title):
            print(f"# [{code}] {e['title']}")
            print(f"出处：{e['period']} · 原文栏目：{e['sec']}")
            print(f"位置：{fn}:{li.get(e['title'], '?')}\n")
            print(e["body"])
            return
    print(f"模块 {code} 内没有标题为「{a.title}」的条目。可用 search 检索正文。")

def cmd_outline(a):
    _, tb = load()
    idx, _ = load()
    for m in tb["modules"]:
        print(f"\n## {m['code']} {m['name']}")
        for e in sort_desc(m["items"]):
            print(f"  [{e['period']}] {e['title']}")

def main():
    ap = argparse.ArgumentParser(description="2026 时政库检索")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    sub.add_parser("outline").set_defaults(fn=cmd_outline)
    p = sub.add_parser("module"); p.add_argument("-c","--code",required=True)
    p.add_argument("--limit",type=int,default=20); p.add_argument("--offset",type=int,default=0)
    p.set_defaults(fn=cmd_module)
    p = sub.add_parser("month"); p.add_argument("-m","--month",required=True)
    p.set_defaults(fn=cmd_month)
    p = sub.add_parser("search"); p.add_argument("-k","--keyword",required=True)
    p.add_argument("--limit",type=int,default=10); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("get"); p.add_argument("-c","--code",required=True)
    p.add_argument("-t","--title",required=True); p.set_defaults(fn=cmd_get)
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a.fn(a)

if __name__ == "__main__":
    main()
