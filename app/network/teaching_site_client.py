"""
Blackboard / PKU teaching site HTTP client.

Responsible only for fetching raw HTML/JSON from the teaching site.
Parsing is handled by the parsers/ layer.
"""

from __future__ import annotations

from app.network.auth_client import AuthSession
from app.network.network_errors import ConnectionError

import requests


# Blackboard base URL
_BB_BASE = "http://course.pku.edu.cn"


class TeachingSiteClient:
    """Fetches raw content from PKU Blackboard."""

    def fetch_courses(self, session: AuthSession) -> str:
        """Return raw HTML of the course list page."""
        url = f"{_BB_BASE}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1"
        return self._get(session, url)

    def fetch_ddl(self, session: AuthSession, semester: str = "") -> str:
        """Return raw HTML of the assignments/DDL page."""
        url = (
            f"{_BB_BASE}/webapps/bb-assignment-BBLEARN/execute/viewStudentSubmissions"
            f"?course_id=_&mode=all"
        )
        return self._get(session, url)

    def fetch_schedule(self, session: AuthSession, semester: str = "") -> str:
        """Return raw content of the course schedule (via Portal portlet)."""
        from app.config import PORTAL_COURSETABLE_URL
        return self._get(session, PORTAL_COURSETABLE_URL)

    def fetch_exams(self, session: AuthSession, semester: str = "") -> str:
        """Return raw HTML of the exam information page."""
        url = f"{_BB_BASE}/webapps/bb-test-BBLEARN/review/exam"
        return self._get(session, url)

    @staticmethod
    def _get(session: AuthSession, url: str) -> str:
        try:
            resp = session.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            raise ConnectionError(f"Request failed [{url}]: {exc}") from exc
