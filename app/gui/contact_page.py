from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import BORDER, INK, PRIMARY, PRIMARY_LIGHT, TEXT


_QR_PATH = Path(__file__).resolve().parent / "assets" / "donate_qrcode.jpg"
_AUTHOR_EMAIL = "enhuayang25@stu.pku.edu.cn"


class ContactPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        title = QLabel("联系作者")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {INK};")
        layout.addWidget(title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(18)
        cards_row.addWidget(self._build_donate_card(), stretch=1)
        cards_row.addWidget(self._build_contact_card(), stretch=1)
        layout.addLayout(cards_row, stretch=1)

    def _build_donate_card(self) -> QFrame:
        card = self._make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        heading = QLabel("请作者吃根鸭腿")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {PRIMARY}; "
            "background: transparent;"
        )
        layout.addWidget(heading)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setStyleSheet("background: transparent;")
        if _QR_PATH.exists():
            pixmap = QPixmap(str(_QR_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    280,
                    280,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                qr_label.setPixmap(scaled)
            else:
                qr_label.setText("（赞赏码图片加载失败）")
        else:
            qr_label.setText("（赞赏码图片缺失）")
        layout.addWidget(qr_label)

        hint = QLabel("扫码即可投喂 🪿")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size: 12px; color: {TEXT}; background: transparent;")
        layout.addWidget(hint)

        layout.addStretch()
        return card

    def _build_contact_card(self) -> QFrame:
        card = self._make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("联系作者")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {PRIMARY}; "
            "background: transparent;"
        )
        layout.addWidget(heading)

        intro = QLabel(
            "欢迎反馈使用问题、提交想要的功能，"
            "也欢迎来信交流任何与本项目相关的话题。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"font-size: 13px; color: {TEXT}; background: transparent; "
            "line-height: 150%;"
        )
        layout.addWidget(intro)

        layout.addSpacing(20)

        email_label = QLabel("邮箱")
        email_label.setStyleSheet(
            f"font-size: 12px; color: {TEXT}; background: transparent;"
        )
        layout.addWidget(email_label)

        email_value = QLabel(_AUTHOR_EMAIL)
        email_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        email_value.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {PRIMARY}; "
            f"background: {PRIMARY_LIGHT}; padding: 8px 12px; "
            f"border: 1px solid {BORDER}; border-radius: 6px;"
        )
        layout.addWidget(email_value)

        copy_hint = QLabel("（点击文字可选中复制）")
        copy_hint.setStyleSheet(
            f"font-size: 11px; color: #9CA3AF; background: transparent;"
        )
        layout.addWidget(copy_hint)

        layout.addStretch()
        return card

    @staticmethod
    def _make_card() -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
            """
        )
        return card


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    page = ContactPage()
    page.resize(720, 520)
    page.show()
    sys.exit(app.exec())
