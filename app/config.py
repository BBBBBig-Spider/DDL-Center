import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")

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

# Mock data (fallback when real sync is unavailable)
MOCK_DDL_PATH = os.path.join(DATA_DIR, "mock_ddl.html")
MOCK_SCHEDULE_PATH = os.path.join(DATA_DIR, "mock_schedule.html")
MOCK_EXAMS_PATH = os.path.join(DATA_DIR, "mock_exams.html")

# AI integration (DeepSeek via OpenAI-compatible API)
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
AI_DAILY_TOKEN_LIMIT = 50_000   # disable AI for the day once this is exceeded
AI_REQUEST_TIMEOUT = 30         # seconds
AI_DEMO_RESPONSES_PATH = os.path.join(DATA_DIR, "ai_demo_responses.json")

