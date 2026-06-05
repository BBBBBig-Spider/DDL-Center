import sys

from PySide6.QtWidgets import QApplication

from app.gui.demo_facade import DemoFacade
from app.gui.main_window import MainWindow


def build_facade():
    try:
        from app.database.database_manager import DatabaseManager
        from app.managers.alert_manager import AlertManager
        from app.managers.app_facade import AppFacade
        from app.managers.task_manager import TaskManager
        from app.repositories.alert_repository import AlertRepository
        from app.repositories.task_repository import TaskRepository

        db_manager = DatabaseManager()
        db_manager.initialize_database()
        task_repository = TaskRepository(db_manager)
        alert_repository = AlertRepository(db_manager)
        task_manager = TaskManager(task_repository)
        alert_manager = AlertManager(task_repository, alert_repository)
        return AppFacade(task_manager, alert_manager)
    except Exception as exc:
        print(f"Backend facade unavailable, using demo data: {exc}")
        return DemoFacade()


def main() -> None:
    app = QApplication(sys.argv)

    window = MainWindow(build_facade())
    window.show()

    print("DDL Command Center started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
