import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QFrame, QApplication)
from PySide6.QtCore import Qt



class AlertItemWidget(QFrame): 
    def __init__(self, alert_obj): 
        super().__init__()
        self.level = getattr(alert_obj, 'level', alert_obj.get('level', 'info'))
        self.kind = getattr(alert_obj, 'kind', alert_obj.get('kind', 'deadline'))
        self.message = getattr(alert_obj, 'message', alert_obj.get('message', '暂无提醒内容'))
        self.init_ui()
    
    def init_ui(self): 
        self.setFixedHeight(50)
        if self.level == "overdue":
            icon_str = "🚨"
            color = "#FF4D4F"       # 刺眼红（已超期）
            bg_color = "#FFF1F0"    # 淡红底
        elif self.level == "urgent":
            icon_str = "🔥"
            color = "#FF4D4F"       # 刺眼红（燃眉之急：1天内）
            bg_color = "#FFF1F0"    # 淡红底
        elif self.level == "warning":
            icon_str = "⏳"
            color = "#FAAD14"       # 警告橙（迫在眉睫：3天内）
            bg_color = "#FFFBE6"    # 淡黄底
        else: # info
            icon_str = "💡"
            color = "#1890FF"       # 提示蓝（常规提醒或进度提醒）
            bg_color = "#E6F7FF"    # 淡蓝底
        
        if self.kind == "overload": 
            icon_str = "⚠️"

        self.setStyleSheet(f"""
            AlertItemWidget {{
                background-color: {bg_color};
                border: 1px solid {color}80;
                border-radius: 6px;
            }}
            AlertItemWidget:hover {{
                border: 1px solid {color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        lbl_icon = QLabel(icon_str)
        lbl_icon.setStyleSheet("font-size: 14px; ")
        layout.addWidget(lbl_icon)

        lbl_msg = QLabel(self.message)
        lbl_msg.setStyleSheet(f"font-weight: 500; font-size: 12px; color: {color if self.level in ['overdue', 'urgent'] else '#333'};")
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg, stretch=1)

class AlertPanel(QWidget): 
    def __init__(self, facade = None): 
        super().__init__()
        self.facade = facade
        self.init_ui()
        self.refresh_display()
    
    def init_ui(self): 
        self.setFixedWidth(300)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(6)

        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 4px; border: 1px solid #E8E8E8;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(8, 6, 8, 6)

        lbl_panel_title = QLabel("预警栏")
        lbl_panel_title.setStyleSheet("color: #262626; font-weight: bold; font-size: 12px;")
        title_layout.addWidget(lbl_panel_title)

        main_layout.addWidget(title_frame)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 4, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def refresh_display(self): 
        while self.list_layout.count(): 
            item = self.list_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
        
        alerts_data = []

        if self.facade and hasattr(self.facade, "generate_alerts"): 
            try: 
                alerts_data = self.facade.generate_alerts()
            except Exception as e: 
                print(f"[GUI Error] 提醒面板调用 Facade 失败: {e}")
        
        else: 
            alerts_data = [
                {"level": "overdue", "kind": "deadline", "message": "高数作业已超期 3 小时！"},
                {"level": "urgent", "kind": "deadline", "message": "程序设计大作业仅剩 4 小时截止！"},
                {"level": "warning", "kind": "deadline", "message": "AI引论的lab还剩 2 天。"},
                {"level": "urgent", "kind": "overload", "message": "警告：5月25日同日包含 4 个 DDL，严重超载！"},
                {"level": "info", "kind": "progress", "message": "本周任务完成率已达到 65%，请继续保持。"},
            ]
        
        if not alerts_data: 
            lbl_empty = QLabel("暂时没有明确的任务！")
            lbl_empty.setStyleSheet("color: #BFBFBF; font-size: 12px; font-style: italic; margin-top: 20px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl_empty)
        else:
            for alert in alerts_data:
                item_widget = AlertItemWidget(alert)
                self.list_layout.addWidget(item_widget)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = AlertPanel(facade=None) 
    panel.setWindowTitle("alert_panel调试")
    panel.resize(320, 450)
    panel.show()
    sys.exit(app.exec())