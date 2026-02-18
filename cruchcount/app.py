from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from cruchcount.db import Database
from cruchcount.ui.main_window import MainWindow


def run_app() -> None:
    app = QApplication([])
    data_dir = Path(__file__).resolve().parent.parent / "data"
    database = Database(data_dir / "cruchcount.db")
    database.init_schema()

    window = MainWindow(database=database)
    window.show()
    app.exec()
    window.database.close()
