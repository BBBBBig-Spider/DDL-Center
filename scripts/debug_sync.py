"""Debug what fetch_ddl actually returns and where lab4 disappears.

Usage (PowerShell, repo root):
    python scripts/debug_sync.py

Writes:
    data/last_fetch.html      raw concatenated HTML returned by fetch_ddl
    data/last_parsed.json     hard-parsed Task list
    data/last_chunks.json     all announcement chunks (one per <li>)

Console summary highlights:
    - course / DDL-link counts
    - hard-parser task count
    - announcement chunk count
    - any chunk whose title or external_id contains 'lab' / '1624444'
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Make `app` importable when running from repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.network.auth_client import AuthClient
from app.network.teaching_site_client import TeachingSiteClient
from app.parsers.ddl_parser import DDLParser


def _load_env_file() -> None:
    """Tiny .env loader so PKU_USERNAME / PKU_PASSWORD can come from disk."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _dump_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> int:
    _load_env_file()
    username = os.getenv("PKU_USERNAME", "")
    password = os.getenv("PKU_PASSWORD", "")
    if not username or not password:
        print("缺少 PKU_USERNAME / PKU_PASSWORD（.env 或环境变量）。")
        return 2

    out_html = ROOT / "data" / "last_fetch.html"
    out_parsed = ROOT / "data" / "last_parsed.json"
    out_chunks = ROOT / "data" / "last_chunks.json"

    print("=== 登录 IAAA ===")
    try:
        session = AuthClient().login(username, password)
    except Exception as exc:
        print("登录失败：")
        traceback.print_exc()
        return 3
    print("OK")

    print("=== fetch_current_semester_ddl ===")
    client = TeachingSiteClient()

    # Manually replay the fetch step-by-step to expose where 0 课程 happens.
    print("--- step-by-step diagnosis ---")
    home_urls = (
        "https://course.pku.edu.cn/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1",
        "https://course.pku.edu.cn/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1",
        "https://course.pku.edu.cn/webapps/portal/execute/tabs/tabAction?tabId=_2_1",
    )
    home_pages = []
    for url in home_urls:
        try:
            page = client._get(session, url)
            home_pages.append((url, page))
            print(f"  home_page OK [{len(page):,} chars] {url}")
        except Exception as exc:
            print(f"  home_page ERR {url} → {exc}")

    seen_courses = set()
    course_links_total = []
    any_anchor = False
    for url, page in home_pages:
        scoped = client._extract_current_semester_course_links(page)
        if scoped is None:
            print(f"  [{url}] 锚点未找到")
            continue
        any_anchor = True
        new = [u for u in scoped if u not in seen_courses]
        seen_courses.update(scoped)
        course_links_total.extend(new)
        print(f"  [{url}] 锚点 OK，本页拿到 {len(scoped)} 个课程链接，新加 {len(new)}")
        for u in scoped[:3]:
            print(f"      e.g.: {u[:160]}")

    if not any_anchor:
        print("  ⚠ 全部 home_page 都没识别到当前学期锚点 → 走 legacy fallback")
        for url, page in home_pages:
            for u in client._extract_course_links(page):
                if u not in seen_courses:
                    seen_courses.add(u)
                    course_links_total.append(u)
        print(f"  legacy 抓到 {len(course_links_total)} 个课程链接")

    print(f"--- 最终课程链接数: {len(course_links_total)} ---")
    if not course_links_total:
        print("⚠ 0 课程链接！这就是 0 task 的根因。")

    # Inspect the first course page: list all <a> tags whose text contains '作业'
    if course_links_total:
        print("\n--- 课程页 a 标签诊断（取第 1 个课程） ---")
        first_url = course_links_total[0]
        try:
            first_page = client._get(session, first_url)
        except Exception as exc:
            print(f"  抓课程页失败: {exc}")
            first_page = ""
        if first_page:
            (ROOT / "data" / "last_course_page.html").write_text(first_page, encoding="utf-8")
            print(f"  saved → data/last_course_page.html ({len(first_page):,} chars)")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(first_page, "lxml")
            # find_all a
            cnt = 0
            cnt_ye = 0
            shown = 0
            for a in soup.find_all("a", href=True):
                text = a.get_text(" ", strip=True)
                cnt += 1
                if "作业" in text:
                    cnt_ye += 1
                    if shown < 12:
                        shown += 1
                        print(f"   contains '作业': text={text!r}  href={a['href'][:140]!r}")
            print(f"  a 标签总数: {cnt}；含'作业'文字的: {cnt_ye}")
            # 直接 grep 文本里有没有"课程作业"
            print(f"  page 直接 grep '课程作业': {first_page.count('课程作业')} 次")

    # 用真实 client.fetch_current_semester_ddl 走一遍（保留原诊断）
    try:
        raw = client.fetch_current_semester_ddl(session)
    except Exception:
        print("fetch 抛错：")
        traceback.print_exc()
        return 4
    _dump_text(out_html, raw)
    print(f"raw HTML: {len(raw):,} chars → {out_html}")

    # Surface any fallback warnings the client recorded
    warnings = getattr(client, "_last_warnings", []) or []
    if warnings:
        print("⚠ client warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("client warnings: (none)")

    course_pages = raw.count('class="ddl-course-page"')
    li_items = raw.count("contentListItem:")
    print(f"  ddl-course-page 块数: {course_pages}")
    print(f"  contentListItem: 出现次数（含重复）: {li_items}")

    parser = DDLParser()

    # NEW: parse_assignment_items — 用于实际 sync 流程的输入
    try:
        items = parser.parse_assignment_items(raw)
    except Exception:
        print("parse_assignment_items 抛错：")
        traceback.print_exc()
        items = []
    items_dump = [
        {
            "external_id": it.get("external_id"),
            "title": it.get("title"),
            "due_time": it.get("due_time").isoformat() if it.get("due_time") else None,
            "course_external_id": it.get("course_external_id"),
            "course_name": it.get("course_name"),
            "description_preview": (it.get("description") or "")[:120],
            "text_preview": (it.get("text") or "")[:120],
        }
        for it in items
    ]
    _dump_json(ROOT / "data" / "last_items.json", items_dump)
    have_due = sum(1 for it in items if it.get("due_time"))
    print(
        f"parse_assignment_items: {len(items)} 条；"
        f"含 due_time {have_due} 条；"
        f"无 due_time {len(items) - have_due} 条 → data/last_items.json"
    )
    # 桶分流摘要
    from datetime import datetime
    now = datetime.now()
    overdue = [it for it in items if it.get("due_time") and it["due_time"] < now]
    future = [it for it in items if it.get("due_time") and it["due_time"] >= now]
    no_due = [it for it in items if not it.get("due_time")]
    print(f"  ↳ 桶 1（逾期，丢）   : {len(overdue)}")
    print(f"  ↳ 桶 2（无 due，AI）: {len(no_due)}")
    print(f"  ↳ 桶 3（未来，写库）: {len(future)}")
    if future:
        print("  桶 3 列表前 5 条：")
        for it in future[:5]:
            print(
                f"    - [{it.get('course_name') or '?'}] {it.get('title') or '?'}"
                f"  due={it.get('due_time')}  ext_id={it.get('external_id')}"
            )

    # Hard parse — 老路径仍跑用于对照
    try:
        tasks = parser.parse(raw)
    except Exception:
        print("DDLParser.parse 抛错：")
        traceback.print_exc()
        tasks = []
    parsed_dump = [
        {
            "title": t.title,
            "due_time": t.due_time.isoformat() if t.due_time else None,
            "external_id": t.external_id,
            "source": t.source,
        }
        for t in tasks
    ]
    _dump_json(out_parsed, parsed_dump)
    print(f"老 parse() 硬识别 task 数: {len(tasks)} → {out_parsed}")

    # Announcement chunks (every li, regardless of recognition)
    try:
        chunks = parser.extract_announcement_chunks(raw)
    except Exception:
        print("extract_announcement_chunks 抛错：")
        traceback.print_exc()
        chunks = []
    chunk_dump = [
        {
            "external_id": c.get("external_id"),
            "title": c.get("title"),
            "course_external_id": c.get("course_external_id"),
            "course_name": c.get("course_name"),
            "text_preview": (c.get("text") or "")[:200],
        }
        for c in chunks
    ]
    _dump_json(out_chunks, chunk_dump)
    print(f"announcement chunks 数: {len(chunks)} → {out_chunks}")

    # lab4 spotlight
    needles = ("lab4", "Lab4", "LAB4", "lab 4", "1624444")
    print("=== 查找 lab4 痕迹 ===")
    matched_chunks = [
        c for c in chunks
        if any(n.lower() in (c.get("title") or "").lower() for n in needles)
        or any(n in (c.get("external_id") or "") for n in needles)
        or any(n.lower() in (c.get("text") or "").lower() for n in needles)
    ]
    if matched_chunks:
        print(f"chunks 命中 {len(matched_chunks)} 条:")
        for c in matched_chunks:
            print(f"  - title={c.get('title')!r}  ext_id={c.get('external_id')!r}  course={c.get('course_external_id')!r}")
    else:
        print("chunks 中没有任何 'lab4' / '1624444' 痕迹 —— fetch_ddl 抓不到这条公告。")

    matched_in_html = "1624444" in raw or "lab4" in raw.lower()
    print(f"raw HTML 直接 grep 命中 'lab4'/'1624444': {matched_in_html}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
