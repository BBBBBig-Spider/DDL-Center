from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import BORDER, INK, MUTED, ACCENT, PRIMARY, PRIMARY_LIGHT, TEXT, secondary_button_style

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    def _install_chinese_font() -> None:
        """Pick the first available CJK-capable font in the system so matplotlib
        no longer emits 'Glyph XXX missing from font' warnings on Chinese labels."""
        import matplotlib
        import matplotlib.font_manager as fm
        candidates = ["Microsoft YaHei", "SimHei", "PingFang SC",
                      "Noto Sans CJK SC", "WenQuanYi Zen Hei", "Arial Unicode MS"]
        available = {f.name for f in fm.fontManager.ttflist}
        chosen = next((c for c in candidates if c in available), None)
        if chosen:
            existing = matplotlib.rcParams.get("font.sans-serif", [])
            # Prepend the chosen font so it wins over DejaVu Sans.
            matplotlib.rcParams["font.sans-serif"] = [chosen] + [
                f for f in existing if f != chosen
            ]
            matplotlib.rcParams["axes.unicode_minus"] = False

    _install_chinese_font()
except Exception:
    FigureCanvas = None
    Figure = None


from app.gui._helpers import get_field


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, hint: str = "", accent: str = PRIMARY, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(
            f"""
            QFrame#metricCard {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-left: 4px solid {accent};
                border-radius: 6px;
            }}
            QFrame#metricCard QLabel {{
                background-color: transparent;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 12px; color: {MUTED};")
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {INK};")
        hint_label = QLabel(hint)
        hint_label.setStyleSheet("font-size: 11px; color: #8A7A7A;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(hint_label)


class StatisticsWindow(QWidget):
    def __init__(self, facade=None, parent=None):
        super().__init__(parent)
        self.facade = facade
        self._chart_canvas = None
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        self.setObjectName("StatisticsWindow")
        self.setStyleSheet(
            f"""
            QWidget#StatisticsWindow {{
                background-color: transparent;
                color: {INK};
            }}
            QWidget#StatisticsWindow QLabel {{
                background-color: transparent;
            }}
            """
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 18, 18, 18)
        self.main_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title_label = QLabel("学习进度统计")
        title_label.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setStyleSheet(secondary_button_style())
        self.refresh_button.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_button)
        self.main_layout.addLayout(header_layout)

        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(10)
        self.main_layout.addLayout(self.metrics_grid)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("ddlChartFrame")
        self.chart_frame.setStyleSheet(
            f"""
            QFrame#ddlChartFrame {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QFrame#ddlChartFrame QLabel {{
                background-color: transparent;
            }}
            """
        )
        self.chart_layout = QVBoxLayout(self.chart_frame)
        self.chart_layout.setContentsMargins(14, 12, 14, 12)
        self.chart_layout.setSpacing(8)
        self.main_layout.addWidget(self.chart_frame, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"background-color: {PRIMARY_LIGHT}; color: {TEXT}; border: 1px solid #E7B8B8; "
            "border-radius: 6px; padding: 10px; font-size: 12px;"
        )
        self.main_layout.addWidget(self.status_label)

    def refresh(self) -> None:
        tasks = self._load_tasks()
        stats = self._build_statistics(tasks)
        self._render_metrics(stats)
        self._render_chart(stats)
        self._render_status(stats)

    def _load_tasks(self) -> list:
        if not self.facade or not hasattr(self.facade, "list_tasks"):
            return []
        try:
            return list(self.facade.list_tasks(None))
        except Exception as exc:
            print(f"[GUI] failed to load tasks for statistics: {exc}")
            return []

    def _load_facade_stats(self) -> dict:
        if not self.facade or not hasattr(self.facade, "get_statistics"):
            return {}
        try:
            raw = self.facade.get_statistics()
        except NotImplementedError:
            return {}
        except Exception as exc:
            print(f"[GUI] failed to load facade statistics: {exc}")
            return {}

        if isinstance(raw, dict):
            return raw
        keys = ["total_tasks", "done_tasks", "active_tasks", "completion_rate"]
        return {key: get_field(raw, key) for key in keys if get_field(raw, key) is not None}

    def _build_statistics(self, tasks: list) -> dict:
        facade_stats = self._load_facade_stats()
        total = int(facade_stats.get("total_tasks") or len(tasks))
        done = int(
            facade_stats.get("done_tasks")
            if facade_stats.get("done_tasks") is not None
            else len([task for task in tasks if get_field(task, "status") == "done"])
        )
        active = int(facade_stats.get("active_tasks") if facade_stats.get("active_tasks") is not None else total - done)
        completion_rate = facade_stats.get("completion_rate")
        if completion_rate is None:
            completion_rate = done / total if total else 0.0

        now = datetime.now()
        overdue = 0
        urgent = 0
        for task in tasks:
            if get_field(task, "status") == "done":
                continue
            due_time = get_field(task, "due_time")
            if not isinstance(due_time, datetime):
                continue
            if due_time < now:
                overdue += 1
            elif due_time <= now + timedelta(days=1):
                urgent += 1

        return {
            "total": total,
            "done": done,
            "active": active,
            "completion_rate": float(completion_rate),
            "due_buckets": self._build_due_buckets(tasks),
            "overdue": overdue,
            "urgent": urgent,
        }

    def _build_due_buckets(self, tasks: list) -> list[tuple[str, int]]:
        today = date.today()
        buckets = []
        for offset in range(7):
            day = today + timedelta(days=offset)
            count = 0
            for task in tasks:
                due_time = get_field(task, "due_time")
                if (
                    isinstance(due_time, datetime)
                    and due_time.date() == day
                    and get_field(task, "status") != "done"
                ):
                    count += 1
            label = "今天" if offset == 0 else day.strftime("%m-%d")
            buckets.append((label, count))
        return buckets

    def _render_metrics(self, stats: dict) -> None:
        self._clear_layout(self.metrics_grid)
        cards = [
            MetricCard("总任务", str(stats["total"]), "当前任务池", PRIMARY),
            MetricCard("已完成", str(stats["done"]), f"完成率 {stats['completion_rate']:.0%}", "#6B7D3A"),
            MetricCard("未完成", str(stats["active"]), "仍需处理", ACCENT),
            MetricCard("紧急 / 逾期", f"{stats['urgent']} / {stats['overdue']}", "24 小时内 / 已逾期", PRIMARY),
        ]
        for index, card in enumerate(cards):
            self.metrics_grid.addWidget(card, 0, index)

    def _render_chart(self, stats: dict) -> None:
        self._clear_layout(self.chart_layout)

        title = QLabel("未来 7 天 DDL 分布")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {INK};")
        self.chart_layout.addWidget(title)

        subtitle = QLabel("仅统计未完成任务的截止时间，用于判断近期压力。")
        subtitle.setStyleSheet(f"font-size: 12px; color: {MUTED};")
        self.chart_layout.addWidget(subtitle)

        values = [count for _label, count in stats["due_buckets"]]
        if sum(values) == 0:
            empty = QLabel("未来 7 天暂无未完成 DDL")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 48px;")
            self.chart_layout.addWidget(empty, stretch=1)
            return

        if FigureCanvas is None or Figure is None:
            fallback = QLabel("当前环境未加载 matplotlib，无法显示图表。")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("color: #9CA3AF; padding: 36px;")
            self.chart_layout.addWidget(fallback, stretch=1)
            return

        labels = [label for label, _count in stats["due_buckets"]]
        max_value = max(values)

        figure = Figure(figsize=(6, 2.8), tight_layout=True, facecolor="#FFFFFF")
        axis = figure.add_subplot(111)
        axis.set_facecolor("#FFFFFF")
        axis.bar(labels, values, color=PRIMARY, width=0.52)
        axis.set_ylim(0, max_value + 1)
        axis.set_ylabel("DDL 数量", color=TEXT)
        axis.tick_params(axis="x", colors=TEXT, labelsize=9)
        axis.tick_params(axis="y", colors=TEXT, labelsize=9)
        axis.grid(axis="y", color="#EFE7E3", linewidth=0.8)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#DDD0CC")
        axis.spines["bottom"].set_color("#DDD0CC")

        for idx, value in enumerate(values):
            if value > 0:
                axis.text(idx, value + 0.05, str(value), ha="center", va="bottom", color=INK, fontsize=9)

        self._chart_canvas = FigureCanvas(figure)
        self._chart_canvas.setStyleSheet("background-color: #FFFFFF;")
        self.chart_layout.addWidget(self._chart_canvas, stretch=1)

    def _render_status(self, stats: dict) -> None:
        if stats["overdue"]:
            text = f"负载状态：存在 {stats['overdue']} 个逾期任务，请优先处理。"
        elif stats["urgent"]:
            text = f"负载状态：未来 24 小时内有 {stats['urgent']} 个任务截止。"
        elif stats["active"] >= 6:
            text = "负载状态：未完成任务偏多，建议使用推荐面板拆分执行时间。"
        else:
            text = "负载状态：当前节奏稳定。"
        self.status_label.setText(text)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
