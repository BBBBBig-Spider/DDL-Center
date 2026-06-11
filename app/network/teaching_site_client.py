"""
Blackboard / PKU teaching site HTTP client.

Responsible only for fetching raw HTML/JSON from the teaching site.
Parsing is handled by the parsers/ layer.
"""

from __future__ import annotations

from html import escape
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from app.network.auth_client import AuthSession
from app.network.network_errors import ConnectionError
from app.config import PKU_VERIFY_SSL

import requests
from urllib3.exceptions import InsecureRequestWarning

if not PKU_VERIFY_SSL:
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# Blackboard base URL
_BB_BASE = "https://course.pku.edu.cn"


class TeachingSiteClient:
    """Fetches raw content from PKU Blackboard."""

    DDL_MENU_KEYWORDS = (
        "课程作业",
        "作业",
        "测验",
        "测试",
        "assignment",
        "test",
        "quiz",
    )

    def __init__(self) -> None:
        self._last_warnings: list[str] = []

    def consume_warnings(self) -> list[str]:
        out = list(self._last_warnings)
        self._last_warnings = []
        return out

    def fetch_courses(self, session: AuthSession) -> str:
        """Return raw HTML of the course list page."""
        url = f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1"
        return self._get(session, url)

    def fetch_current_semester_ddl(self, session: AuthSession) -> str:
        """Return raw HTML for current-semester courses' assignment pages only.

        Same return shape as the legacy ``fetch_ddl`` (each course's
        assignment list page is wrapped in
        ``<div class="ddl-course-page" data-course-name=... data-course-external-id=...>``)
        but courses outside ``<span class="moduleTitle">当前学期课程</span>``
        are excluded; if the anchor is missing, falls back to the legacy
        link extractor and records a warning on ``_last_warnings``.
        """
        self._last_warnings = []
        home_urls = (
            f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1",
            f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1",
            f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tabId=_2_1",
        )
        home_pages: list[str] = []
        course_links: list[str] = []
        seen_courses: set[str] = set()
        any_anchor_found = False
        for home_url in home_urls:
            try:
                home_page = self._get(session, home_url)
            except ConnectionError:
                continue
            home_pages.append(home_page)
            scoped = self._extract_current_semester_course_links(home_page)
            if scoped is None:
                continue
            any_anchor_found = True
            for course_url in scoped:
                if course_url not in seen_courses:
                    seen_courses.add(course_url)
                    course_links.append(course_url)

        if not any_anchor_found:
            self._last_warnings.append("未识别到当前学期分组，已退回旧版课程链接扫描")
            for home_page in home_pages:
                for course_url in self._extract_course_links(home_page):
                    if course_url not in seen_courses:
                        seen_courses.add(course_url)
                        course_links.append(course_url)

        pages: list[str] = []
        seen: set[str] = set()
        for course_url in course_links:
            try:
                course_page = self._get(session, course_url)
            except ConnectionError:
                continue
            course_name = self._extract_course_name(course_page)
            course_external_id = self._extract_course_external_id(course_url)
            assignment_url = self._extract_assignment_link(course_page)
            if assignment_url is None:
                # No precise "课程作业" sidebar entry → skip this course
                # entirely. Courses without an assignments menu (e.g.
                # humanities seminars, PE) shouldn't trigger AI fallback
                # or keyword guessing.
                continue
            ddl_urls = [assignment_url]
            for ddl_url in ddl_urls:
                if ddl_url in seen:
                    continue
                seen.add(ddl_url)
                try:
                    ddl_page = self._get(session, ddl_url)
                except ConnectionError:
                    continue
                pages.append(
                    '<div class="ddl-course-page" '
                    f'data-course-name="{escape(course_name, quote=True)}" '
                    f'data-course-external-id="{escape(course_external_id, quote=True)}">'
                    f"{ddl_page}</div>"
                )

        if not pages:
            return "\n".join(home_pages)
        return "\n".join(pages)

    def fetch_ddl(self, session: AuthSession, semester: str = "") -> str:
        """Backward-compat alias forwarding to ``fetch_current_semester_ddl``."""
        return self.fetch_current_semester_ddl(session)

    def fetch_schedule(self, session: AuthSession, semester: str = "") -> str:
        """Return raw content of the course schedule (via Portal portlet)."""
        from app.config import PORTAL_COURSETABLE_URL
        return self._get(session, PORTAL_COURSETABLE_URL)

    def fetch_exams(self, session: AuthSession, semester: str = "") -> str:
        """Return raw HTML of the exam information page."""
        url = f"{_BB_BASE}/webapps/bb-test-BBLEARN/review/exam"
        return self._get(session, url)

    def _extract_course_links(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        seen: set[str] = set()
        for node in soup.find_all("a", href=True):
            href = node["href"]
            haystack = f"{node.get_text(' ', strip=True)} {href}".lower()
            if not any(marker in haystack for marker in ("type=course", "course_id", "course_id=", "courseid", "/course/")):
                continue
            url = urljoin(_BB_BASE, href)
            if url not in seen:
                seen.add(url)
                links.append(url)
        return links

    @staticmethod
    def _extract_course_external_id(url: str) -> str:
        import re
        from urllib.parse import unquote

        # Plain "course_id=_98087_1" — most direct ?course_id= URLs use this.
        match = re.search(r"course_id=([^&'\"\s<>]+)", url, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Portal launcher form: "launcher?type=Course&id=PkId{key=_96253_1,...}".
        # Try once verbatim, then once URL-decoded (some hrefs come encoded).
        for candidate in (url, unquote(url)):
            match = re.search(r"key=(_[A-Za-z0-9]+_\d+)", candidate)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_course_name(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        selectors = ("title", "h1", ".courseTitle", "#courseMenuPalette div.navPaletteContent")
        for selector in selectors:
            node = soup.select_one(selector)
            if node is None:
                continue
            text = node.get_text(" ", strip=True)
            if text:
                return TeachingSiteClient._clean_course_name(text)
        return ""

    @staticmethod
    def _clean_course_name(text: str) -> str:
        text = " ".join(text.split())
        for sep in ("–", "—", "-"):
            if sep in text:
                text = text.split(sep, 1)[-1].strip()
                break
        if text.startswith("课程菜单:"):
            text = text.removeprefix("课程菜单:").strip()
        for marker in ("课程通知", "教学大纲", "教学内容", "作业"):
            if marker in text:
                text = text.split(marker, 1)[0].strip()
        return text[:120]

    def _extract_ddl_links(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        seen: set[str] = set()
        for node in soup.find_all("a", href=True):
            href = node["href"]
            text = node.get_text(" ", strip=True)
            haystack = f"{text} {href}".lower()
            if not any(keyword.lower() in haystack for keyword in self.DDL_MENU_KEYWORDS):
                continue
            if "gradebook" in haystack or "成绩" in haystack:
                continue
            url = urljoin(_BB_BASE, href)
            if url not in seen:
                seen.add(url)
                links.append(url)
        return links

    def _extract_current_semester_course_links(self, html: str) -> list[str] | None:
        """Return current-semester-only course links, or None if anchor missing."""
        soup = BeautifulSoup(html, "lxml")
        anchor = None
        for span in soup.find_all("span", class_="moduleTitle"):
            if span.get_text(strip=True) == "当前学期课程":
                anchor = span.find_parent(["h1", "h2", "h3", "h4"]) or span
                break
        if anchor is None:
            return None

        links: list[str] = []
        seen: set[str] = set()
        for node in anchor.find_all_next():
            if node is anchor:
                continue
            # The portal layout puts the section title in <h2>, with <h3>
            # subtitles INSIDE the section ("您有新课程加入您的学生角色").
            # Only break on the next <h2> (i.e. the next sibling section
            # such as "历史课程"). h3/h4 are subsections to keep walking.
            if node.name == "h2" and node is not anchor:
                break
            if node.name != "a" or not node.has_attr("href"):
                continue
            href = node["href"]
            href_l = href.lower()
            # Accept either ?course_id=, /courses/<id>, or the portal launcher
            # form ("launcher?type=Course&id=PkId{key=_98087_1,...}").
            if not (
                "course_id=" in href_l
                or "/courses/" in href_l
                or "type=course" in href_l
                or "courseid" in href_l
                or "key=_" in href
            ):
                continue
            url = urljoin(_BB_BASE, href)
            if url in seen:
                continue
            seen.add(url)
            links.append(url)
        return links

    def _extract_assignment_link(self, course_page: str) -> str | None:
        """Find the precise '课程作业' sidebar link; return None if absent."""
        soup = BeautifulSoup(course_page, "lxml")
        for node in soup.find_all("a", href=True):
            text = node.get_text(" ", strip=True)
            if text == "课程作业":
                return urljoin(_BB_BASE, node["href"])
        return None

    @staticmethod
    def _get(session: AuthSession, url: str) -> str:
        try:
            resp = session.session.get(url, timeout=15, verify=PKU_VERIFY_SSL)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            raise ConnectionError(f"Request failed [{url}]: {exc}") from exc
