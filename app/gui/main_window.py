import sys

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QApplication

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = MainWindow(facade=None)
    test_widget.setWindowTitle("DDL Center - 主界面调试")
    test_widget.resize(1000, 700)
    test_widget.show()
    sys.exit(app.exec())