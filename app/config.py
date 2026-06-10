import os
from datetime import date

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements
    load_dotenv = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")

if load_dotenv is not None:
    load_dotenv(os.path.join(ROOT_DIR, ".env"))

DB_PATH = os.path.join(DATA_DIR, "ddl_center.db")
DB_BACKUP_PATH = os.path.join(DATA_DIR, "ddl_center_backup.db")

# Alert thresholds
ALERT_DAYS_WARNING = 3
ALERT_DAYS_URGENT = 1
OVERLOAD_THRESHOLD = 3      # same-day DDL count that triggers overload warning
CLOSE_DEADLINE_HOURS = 24   # gap between DDLs that triggers close-deadline warning

# PKU IAAA authentication
IAAA_BASE_URL = "https://iaaa.pku.edu.cn/iaaa"
IAAA_LOGIN_URL = f"{IAAA_BASE_URL}/oauthlogin.do"
IAAA_PUBKEY_URL = f"{IAAA_BASE_URL}/getPublicKey.do"

# PKU Blackboard
BB_APPID = "blackboard"
BB_REDIR_URL = (
    "http://course.pku.edu.cn/webapps/bb-sso-BBLEARN/execute/authValidate/campusLogin"
)

# PKU Portal (for course table)
PORTAL_APPID = "portal2017"
PORTAL_REDIR_URL = "https://portal.pku.edu.cn/portal2017/ssoLogin.do"
PORTAL_COURSETABLE_URL = (
    "https://portal.pku.edu.cn/portal2017/util/portletRedir.do?portletId=coursetable"
)

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(ROOT_DIR, "data", "ddl_center.log")

# TLS verification for IAAA / Blackboard / Portal requests.
# PKU's cert chain isn't always present in the system CA bundle (certifi
# doesn't carry CFCA/校内 CA), so verify is OFF by default — turning it on
# breaks login on most campus networks. Set PKU_VERIFY_SSL=1 in .env to
# opt in to strict verification when your CA bundle is set up correctly.
_verify_ssl_env = os.getenv("PKU_VERIFY_SSL", "").strip().lower()
PKU_VERIFY_SSL = _verify_ssl_env in {"1", "true", "yes", "on"}

# AI fallback for unrecognized announcements during sync.
# Default ON: hard parser runs first, then any leftover Blackboard items get
# sent through the LLM to recover task/exam shapes. Set PKU_SYNC_AI_FALLBACK=0
# to disable (e.g. when offline or to limit AI cost).
_ai_fallback_env = os.getenv("PKU_SYNC_AI_FALLBACK", "1").strip().lower()
PKU_SYNC_AI_FALLBACK = _ai_fallback_env not in {"0", "false", "no", "off"}

# Mock data (fallback when real sync is unavailable)
MOCK_DDL_PATH = os.path.join(DATA_DIR, "mock_ddl.html")
MOCK_SCHEDULE_PATH = os.path.join(DATA_DIR, "mock_schedule.html")
MOCK_EXAMS_PATH = os.path.join(DATA_DIR, "mock_exams.html")

# AI integration (DeepSeek via OpenAI-compatible API)
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
def _parse_token_limit(raw: str | None) -> float:
    """0 / 'unlimited' / '∞' / negative → no cap (math.inf)."""
    if not raw:
        return float("inf")
    value = raw.strip().lower()
    if value in ("", "0", "unlimited", "infinity", "inf", "∞", "none"):
        return float("inf")
    try:
        parsed = int(value)
    except ValueError:
        return float("inf")
    return float("inf") if parsed <= 0 else float(parsed)


AI_DAILY_TOKEN_LIMIT = _parse_token_limit(os.getenv("AI_DAILY_TOKEN_LIMIT"))
AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "30"))

# Semester start date (override via SEMESTER_START env var, format YYYY-MM-DD)
_semester_start_env = os.getenv("SEMESTER_START", "2026-03-02")
try:
    SEMESTER_START = date.fromisoformat(_semester_start_env)
except ValueError:
    SEMESTER_START = date(2026, 3, 2)

