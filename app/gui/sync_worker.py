from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class SyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, facade, username: str, password: str) -> None:
        super().__init__()
        self.facade = facade
        self.username = username
        self.password = password

    def run(self) -> None:
        try:
            result = self.facade.sync_from_teaching_site(self.username, self.password)
        except NotImplementedError:
            self.failed.emit("后端暂未实现教学网同步接口。")
            return
        except Exception as exc:
            self.failed.emit(f"同步失败：{exc}")
            return
        self.finished.emit(result)
