import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.gui.theme import application_style


_ASSETS = Path(__file__).resolve().parent / "gui" / "assets"
APP_ICON_ICO = _ASSETS / "app_icon.ico"
APP_ICON_PNG = _ASSETS / "app_icon.png"
# Windows-only: a unique AppUserModelID makes the taskbar attach our QIcon
# instead of grouping us under the python.exe icon. Format: company.product.subproduct.version
WINDOWS_APP_ID = "RoastSpider.DDLCenter.App.1"


def _load_app_icon() -> QIcon:
    """Prefer .ico (multi-DPI on Windows); fall back to PNG."""
    if APP_ICON_ICO.exists():
        return QIcon(str(APP_ICON_ICO))
    if APP_ICON_PNG.exists():
        return QIcon(str(APP_ICON_PNG))
    return QIcon()


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        # Non-fatal: taskbar will fall back to the python.exe icon.
        pass


def build_facade():
    from app.config import PKU_SYNC_AI_FALLBACK
    from app.database.database_manager import DatabaseManager
    from app.managers.ai_assistant_manager import AIAssistantManager
    from app.managers.alert_manager import AlertManager
    from app.managers.app_facade import AppFacade
    from app.managers.course_manager import CourseManager
    from app.managers.exam_manager import ExamManager
    from app.managers.recommendation_manager import RecommendationManager
    from app.managers.schedule_manager import ScheduleManager
    from app.managers.statistics_manager import StatisticsManager
    from app.managers.sync_manager import SyncManager
    from app.managers.task_manager import TaskManager
    from app.network.auth_client import AuthClient
    from app.network.teaching_site_client import TeachingSiteClient
    from app.parsers.ddl_parser import DDLParser
    from app.parsers.exam_parser import ExamParser
    from app.parsers.schedule_parser import ScheduleParser
    from app.repositories.alert_repository import AlertRepository
    from app.repositories.course_repository import CourseRepository
    from app.repositories.exam_repository import ExamRepository
    from app.repositories.schedule_repository import ScheduleRepository
    from app.repositories.setting_repository import SettingRepository
    from app.repositories.sync_repository import SyncRepository
    from app.repositories.task_repository import TaskRepository

    db_manager = DatabaseManager()
    db_manager.initialize_database()

    task_repository = TaskRepository(db_manager)
    course_repository = CourseRepository(db_manager)
    schedule_repository = ScheduleRepository(db_manager)
    exam_repository = ExamRepository(db_manager)
    alert_repository = AlertRepository(db_manager)
    sync_repository = SyncRepository(db_manager)
    setting_repository = SettingRepository(db_manager)

    task_manager = TaskManager(task_repository)
    course_manager = CourseManager(course_repository)
    schedule_manager = ScheduleManager(schedule_repository)
    exam_manager = ExamManager(exam_repository)
    alert_manager = AlertManager(task_repository, alert_repository)
    statistics_manager = StatisticsManager(task_manager)
    recommendation_manager = RecommendationManager(task_manager, schedule_manager)
    ai_assistant_manager = AIAssistantManager(
        task_manager=task_manager,
        alert_manager=alert_manager,
        statistics_manager=statistics_manager,
        setting_repository=setting_repository,
        schedule_manager=schedule_manager,
        course_manager=course_manager,
    )
    sync_manager = SyncManager(
        auth_client=AuthClient(),
        teaching_site_client=TeachingSiteClient(),
        ddl_parser=DDLParser(),
        schedule_parser=ScheduleParser(),
        exam_parser=ExamParser(),
        task_repository=task_repository,
        course_repository=course_repository,
        schedule_repository=schedule_repository,
        exam_repository=exam_repository,
        sync_repository=sync_repository,
        ai_assistant_manager=ai_assistant_manager,
        ai_fallback_enabled=PKU_SYNC_AI_FALLBACK,
    )

    facade = AppFacade(
        task_manager=task_manager,
        alert_manager=alert_manager,
        course_manager=course_manager,
        exam_manager=exam_manager,
        schedule_manager=schedule_manager,
        recommendation_manager=recommendation_manager,
        statistics_manager=statistics_manager,
        sync_manager=sync_manager,
        ai_assistant_manager=ai_assistant_manager,
    )
    facade.db_manager = db_manager
    facade.alert_repository = alert_repository
    facade.setting_repository = setting_repository
    return facade


def main() -> None:
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setStyleSheet(application_style())

    icon = _load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow(build_facade())
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    print("DDL Command Center started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
