def reate_task(data: dict) -> int :
    raise NotImplementedError
def update_task(task_id: int, data: dict) -> None :
    raise NotImplementedError
def delete_task(task_id: int) -> None :
    raise NotImplementedError
def list_tasks(filters: dict | None = None) -> list[Task] :
    raise NotImplementedError
def mark_task_done(task_id: int) -> None :
    raise NotImplementedError

def list_courses() -> list[Course] :
    raise NotImplementedError
def list_exams(course_id: int | None = None) -> list[Exam] :
    raise NotImplementedError

def list_schedule(weekday: int, week: int) -> list[ScheduleSlot] :
    raise NotImplementedError
def get_free_slots(weekday: int, week: int) -> list[ScheduleSlot] :
    raise NotImplementedError

def generate_alerts() -> list[Alert] :
    raise NotImplementedError
def recommend_for_task(task_id: int) -> list[ScheduleSlot] :
    raise NotImplementedError

def sync_from_teaching_site(username: str, password: str) -> SyncResult :
    raise NotImplementedError
def get_statistics() -> StatisticsData :
    raise NotImplementedError

# ─── AI 相关 ───
def ai_decompose_task(description: str, due_time: datetime) -> list[dict] :  # 功能 1
    raise NotImplementedError
def ai_chat(conversation_id: int | None, user_msg: str, 
            context_task_id: int | None = None) -> tuple[int, str] :         # 功能 3
    raise NotImplementedError
def ai_generate_briefing() -> str :                                          # 功能 4
    raise NotImplementedError
def ai_summarize_ddl(raw_text: str) -> str :                                 # 功能 5
    raise NotImplementedError

# ─── AI 设置 ───
def set_deepseek_api_key(key: str) -> None :
    raise NotImplementedError
def get_deepseek_api_key() -> str | None :
    raise NotImplementedError
def test_deepseek_api_key(key: str) -> bool :
def ai_is_available() -> bool :                  # Key 已配且未超额时返回 True
    raise NotImplementedError
def ai_today_token_usage() -> int :              # 今日已用 token 数
    raise NotImplementedError