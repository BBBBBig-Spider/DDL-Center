import sys
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

class MockFacade:
    pass


def main() -> None:
    app = QApplication(sys.argv)

    facade = MockFacade() # 暂时用假的
    window = MainWindow(facade)
    window.show()

    window.show()
    print("DDL Command Center started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()