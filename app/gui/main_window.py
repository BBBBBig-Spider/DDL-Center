import sys

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QApplication
from app.gui.task_list_widget import TaskListWidget

class MainWindow(QMainWindow): 
    def __init__(self, facade): 
        super().__init__()
        self.facade = facade
        self.setWindowTitle("DDL指挥中心")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QHBoxLayout(central_widget)
        self.setup_sidebar()

        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area, stretch = 4)

        welcome_label = QLabel("欢迎来到DDL指挥中心！请选择左侧功能。🕷️")
        self.content_area.addWidget(welcome_label)

        self.task_list_page = TaskListWidget(facade = self.facade)
        self.content_area.addWidget(self.task_list_page)

        self.schedule_placeholder = QLabel("课表视图正在开发中，敬请期待！📅")
        self.content_area.addWidget(self.schedule_placeholder)
        self.ai_placeholder = QLabel("AI助手功能正在开发中，敬请期待！🤖")
        self.content_area.addWidget(self.ai_placeholder)

        self.connect_signals()

    def setup_sidebar(self): 
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)

        self.btn_schedule = QPushButton("🕒课表视图")
        self.btn_tasks = QPushButton("📋任务列表")
        self.btn_ai = QPushButton("🤖AI助手")

        sidebar_layout.addWidget(self.btn_schedule)
        sidebar_layout.addWidget(self.btn_tasks)
        sidebar_layout.addWidget(self.btn_ai)

        sidebar_layout.addStretch()

        self.main_layout.addWidget(sidebar_widget, stretch = 1)

    def connect_signals(self):
        self.btn_schedule.clicked.connect(lambda: self.content_area.setCurrentWidget(self.schedule_placeholder))
        self.btn_tasks.clicked.connect(lambda: self.content_area.setCurrentWidget(self.task_list_page))
        self.btn_ai.clicked.connect(lambda: self.content_area.setCurrentWidget(self.ai_placeholder))
    
    def switch_to_task_list(self):
        self.content_area.setCurrentWidget(self.task_list_page)

        if hasattr(self.task_list_page, "refresh_display"):
            self.task_list_page.refresh_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = MainWindow(facade=None)
    test_widget.setWindowTitle("DDL Center - 主界面调试")
    test_widget.resize(1000, 700)
    test_widget.show()
    sys.exit(app.exec())
