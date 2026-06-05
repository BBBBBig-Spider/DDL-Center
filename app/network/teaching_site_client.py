"""
Blackboard / PKU teaching site HTTP client.

Responsible only for fetching raw HTML/JSON from the teaching site.
Parsing is handled by the parsers/ layer.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from app.network.auth_client import AuthSession
from app.network.network_errors import ConnectionError

import requests
from urllib3.exceptions import InsecureRequestWarning

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

    def fetch_courses(self, session: AuthSession) -> str:
        """Return raw HTML of the course list page."""
        url = f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1"
        return self._get(session, url)

    def fetch_ddl(self, session: AuthSession, semester: str = "") -> str:
        """Return raw HTML collected from course assignment/test pages.

        Blackboard does not expose a single global DDL endpoint on the current
        PKU deployment. The reliable flow is:

        1. open the logged-in portal page;
        2. find course launcher links;
        3. enter each course and find menu entries such as "课程作业"/"测验";
        4. concatenate those content pages for DDLParser.
        """
        home = self._get(session, f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1")
        course_links = self._extract_course_links(home)
        pages: list[str] = []
        seen: set[str] = set()

        for course_url in course_links:
            try:
                course_page = self._get(session, course_url)
            except ConnectionError:
                continue
            for ddl_url in self._extract_ddl_links(course_page):
                if ddl_url in seen:
                    continue
                seen.add(ddl_url)
                try:
                    pages.append(self._get(session, ddl_url))
                except ConnectionError:
                    continue

        if not pages:
            return home
        return "\n".join(pages)

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
            if "type=Course" not in href:
                continue
            url = urljoin(_BB_BASE, href)
            if url not in seen:
                seen.add(url)
                links.append(url)
        return links

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

    @staticmethod
    def _get(session: AuthSession, url: str) -> str:
        try:
            resp = session.session.get(url, timeout=15, verify=False)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            raise ConnectionError(f"Request failed [{url}]: {exc}") from exc
