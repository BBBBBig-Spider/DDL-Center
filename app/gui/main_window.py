import sys

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QApplication
from app.gui.task_list_widget import TaskListWidget
from app.gui.schedule_widget import ScheduleWidget

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

        self.schedule_page = ScheduleWidget(facade = self.facade)
        self.content_area.addWidget(self.schedule_page)
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
        self.btn_schedule.clicked.connect(lambda: self.content_area.setCurrentWidget(self.schedule_page))
        self.btn_tasks.clicked.connect(lambda: self.content_area.setCurrentWidget(self.task_list_page))
        self.btn_ai.clicked.connect(lambda: self.content_area.setCurrentWidget(self.ai_placeholder))
    
    def switch_to_task_list(self):
        self.content_area.setCurrentWidget(self.task_list_page)

        if hasattr(self.task_list_page, "refresh_display"):
            self.task_list_page.refresh_display()

if __name__ == "__main__":
    from datetime import datetime
    
    # 1. 尝试导入真实后端组件
    try:
        from app.managers.app_facade import AppFacade
        from app.managers.task_manager import TaskManager
        from app.managers.alert_manager import AlertManager
        from app.repositories.task_repository import TaskRepository
        from app.database.database_manager import DatabaseManager
        BACKEND_IMPORTS_OK = True
    except ImportError:
        BACKEND_IMPORTS_OK = False

    app = QApplication(sys.argv)
    real_facade = None

    if BACKEND_IMPORTS_OK:
        try:
            real_db_manager = DatabaseManager()
            try: real_db_manager.initialize_database()
            except: pass

            real_task_repo = TaskRepository(db_manager=real_db_manager)
            try:
                from app.repositories.alert_repository import AlertRepository
                real_alert_repo = AlertRepository(db_manager=real_db_manager)
            except:
                real_alert_repo = None

            real_task_manager = TaskManager(task_repository=real_task_repo)
            real_alert_manager = AlertManager(task_repository=real_task_repo, alert_repository=real_alert_repo)

            raw_facade = AppFacade(task_manager=real_task_manager, alert_manager=real_alert_manager)
            
            # 预跑核心方法，若无表或数据不完整，直接抛错进盾牌保底
            test_res = raw_facade.list_tasks()
            if not test_res or len(test_res) == 0:
                raise RuntimeError("后端数据库为空或未初始化，启用高仿盾牌模式。")
                
            raw_facade.generate_alerts()
            real_facade = raw_facade
            print("✅ [联调成功] 真实后端完全健康，已硬连真Facade！")
        except Exception as e:
            print(f"⚠️ [联调提示] 真实后端无数据或存在Bug ({e})，启用本地全页面防爆盾模式。")
            real_facade = None

    # ─── 🛡️ 终极全页面适配防爆盾 ───
    if real_facade is None:
        class SafeFacadeBridge:
            def __init__(self):

                class SmartObject:
                    def __init__(self, data):
                        self.__dict__['_data'] = data
                    def __getattr__(self, item):
                        return self._data.get(item, None)
                    def __getitem__(self, item):
                        return self._data.get(item, None)
                    def get(self, key, default=None):
                        return self._data.get(key, default)
                    def keys(self):
                        return self._data.keys()

                self.course_repository = SmartObject({
                    "list_all": lambda: [
                        SmartObject({"id": 101, "name": "高等数学(A)"}),
                        SmartObject({"id": 102, "name": "编译原理"}),
                        SmartObject({"id": 103, "name": "计算概论"})
                    ]
                })

                self.raw_tasks = [
                    {"id": 1, "title": "高数课后习题 1-5", "course_id": 101, "course_name": "高等数学(A)", "description": "周五前交", "due_time": datetime(2026, 6, 1, 23, 59), "estimated_hours": 2.0, "status": "todo", "priority": 1},
                    {"id": 2, "title": "编译原理：词法分析器", "course_id": 102, "course_name": "编译原理", "description": "实验一", "due_time": datetime(2026, 6, 3, 12, 0), "estimated_hours": 8.0, "status": "doing", "priority": 2},
                    {"id": 3, "title": "期中模拟上机测验", "course_id": 103, "course_name": "计算概论", "description": "真题练习", "due_time": datetime(2026, 6, 5, 18, 0), "estimated_hours": 3.0, "status": "done", "priority": 3},
                    {"id": 4, "title": "高数阶段小测准备", "course_id": 101, "course_name": "高等数学(A)", "description": "复习前三章", "due_time": datetime(2026, 5, 29, 9, 0), "estimated_hours": 1.0, "status": "todo", "priority": 1}
                ]
                self.mock_tasks = [SmartObject(t) for t in self.raw_tasks]

                self.raw_alerts = [
                    {"level": "overdue", "kind": "deadline", "message": "高数作业已超期 3 小时！"},
                    {"level": "urgent", "kind": "deadline", "message": "编译原理大作业仅剩 4 小时截止！"},
                    {"level": "warning", "kind": "deadline", "message": "计算概论真题集还剩 2 天截止。"}
                ]
                self.mock_alerts = [SmartObject(a) for a in self.raw_alerts]

            def list_tasks(self, filters=None):
                # 智能过滤器，完美适配列表、时间轴、看板的过滤动作
                if filters and "status" in filters and filters["status"]:
                    return [t for t in self.mock_tasks if t.get("status") == filters["status"]]
                if filters and "course_id" in filters and filters["course_id"]:
                    return [t for t in self.mock_tasks if t.get("course_id") == int(filters["course_id"])]
                return self.mock_tasks

            def create_task(self, data): return 1
            def update_task(self, t_id, data): pass
            def delete_task(self, t_id): pass
            def mark_task_done(self, t_id): pass

            def generate_alerts(self):
                # 抛出具有全兼容特性的百变提醒对象
                return self.mock_alerts

        real_facade = SafeFacadeBridge()

    main_win = MainWindow(facade = real_facade)
    main_win.show()
    sys.exit(app.exec())