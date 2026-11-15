#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时政题库抽题/组卷工具。

用法:
  python quiz.py list
  python quiz.py draw -c 03 -n 10                    # 抽 10 题（不含答案）
  python quiz.py draw -c 03 -n 10 --with-answer      # 带答案解析
  python quiz.py draw -c 03 -n 10 --period 2026年10月下
  python quiz.py paper -n 30                         # 跨模块组卷
  python quiz.py paper -n 30 --seed 123 --with-answer
  python quiz.py answer -c 03 -n 1 2 5               # 按题号取答案
"""
import argparse, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF  = os.path.join(os.path.dirname(HERE), "references")

def load():
    with open(os.path.join(REF, "qbank.json"), encoding="utf-8") as f:
        return json.load(f)

def period_key(period):
    m = re.match(r'2026年(\d{1,2})月(上|下)', period)
    if not m: return (0, 0)
    return (int(m.group(1)), 0 if m.group(2) == "下" else 1)

def sort_desc(items):
    return sorted(items, key=lambda e: (-period_key(e["period"])[0], period_key(e["period"])[1]))

def show(q, i, with_answer=False):
    kind = "多选" if "多选" in q["kind"] else "单选"
    print(f"\n{i}. 〔{kind}〕〔{q['period']}〕")
    for s in q["stem"]:
        print("   " + s)
    for o in q["options"]:
        print("   " + o)
    if with_answer:
        print(f"   ★答案：{q['answer'] or '（原文未给）'}")
        if q["analysis"]:
            print("   ★解析：" + q["analysis"])

def cmd_list(a):
    qb = load()
    tot = sum(len(m["items"]) for m in qb["modules"])
    print(f"时政题库 ｜ {len(qb['modules'])} 个模块 ｜ 共 {tot} 题\n")
    print(f"{'码':<4}{'模块':<28}{'题量':>5}")
    print("-" * 44)
    for m in qb["modules"]:
        print(f"{m['code']:<4}{m['name']:<28}{len(m['items']):>5}")

def cmd_draw(a):
    qb = load()
    code = a.code.zfill(2)
    mod = next((m for m in qb["modules"] if m["code"] == code), None)
    if not mod:
        print("模块不存在。可用模块：", ", ".join(m["code"] for m in qb["modules"])); return
    items = sort_desc(mod["items"])
    if a.period:
        items = [q for q in items if q["period"] == a.period]
        if not items:
            print(f"模块 {code} 在 {a.period} 没有题目"); return
    rnd = random.Random(a.seed) if a.seed is not None else random
    pick = items if a.n >= len(items) else rnd.sample(items, a.n)
    if a.ordered:
        pick = sorted(pick, key=lambda q: -period_key(q["period"])[0])
    print(f"# {mod['code']} {mod['name']} ｜ 抽 {len(pick)} 题"
          f"{'（含答案解析）' if a.with_answer else '（不含答案）'}")
    for i, q in enumerate(pick, 1):
        show(q, i, a.with_answer)

def cmd_paper(a):
    qb = load()
    rnd = random.Random(a.seed) if a.seed is not None else random
    allq = []
    for m in qb["modules"]:
        for q in m["items"]:
            allq.append((m["code"], m["name"], q))
    n = min(a.n, len(allq))
    pick = rnd.sample(allq, n)
    pick.sort(key=lambda x: (-period_key(x[2]["period"])[0]))
    print(f"# 2026 时政模拟卷 ｜ 共 {n} 题"
          f"{'（含答案解析）' if a.with_answer else '（不含答案，做完再对）'}")
    print("# 建议用时：%d 分钟" % max(10, round(n * 0.7)))
    for i, (code, name, q) in enumerate(pick, 1):
        show(q, i, a.with_answer)
        print(f"   〔模块 {code} {name}〕")

def cmd_answer(a):
    qb = load()
    code = a.code.zfill(2)
    mod = next((m for m in qb["modules"] if m["code"] == code), None)
    if not mod: print("模块不存在"); return
    want = set(a.num)
    for i, q in enumerate(mod["items"], 1):
        if i in want:
            print(f"\n{i}. 【答案】{q['answer'] or '（原文未给）'}")
            if q["analysis"]:
                print("   解析：" + q["analysis"])
    print(f"\n# 模块 {code} {mod['name']} 共 {len(mod['items'])} 题")

def main():
    ap = argparse.ArgumentParser(description="2026 时政题库抽题")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)

    p = sub.add_parser("draw")
    p.add_argument("-c","--code",required=True)
    p.add_argument("-n",type=int,default=10)
    p.add_argument("--period",default=None)
    p.add_argument("--seed",type=int,default=None)
    p.add_argument("--with-answer",action="store_true")
    p.add_argument("--ordered",action="store_true")
    p.set_defaults(fn=cmd_draw)

    p = sub.add_parser("paper")
    p.add_argument("-n",type=int,default=30)
    p.add_argument("--seed",type=int,default=None)
    p.add_argument("--with-answer",action="store_true")
    p.set_defaults(fn=cmd_paper)

    p = sub.add_parser("answer")
    p.add_argument("-c","--code",required=True)
    p.add_argument("num",type=int,nargs="+")
    p.set_defaults(fn=cmd_answer)

    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a.fn(a)

if __name__ == "__main__":
    main()
