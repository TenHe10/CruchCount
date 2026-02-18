from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cruchcount.db import Database
from cruchcount.ui.pages.cart_page import CartPage
from cruchcount.ui.pages.inventory_page import InventoryPage


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("CruchCount")
        self.resize(1180, 760)
        self.setStyleSheet(
            """
            QWidget {
                font-size: 16px;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                min-height: 40px;
            }
            QPushButton {
                min-height: 42px;
                padding: 0 14px;
            }
            QTableWidget {
                font-size: 15px;
            }
            QHeaderView::section {
                font-size: 15px;
                padding: 6px;
            }
            """
        )

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        nav_layout = QVBoxLayout()
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.inventory_button = QPushButton("入库")
        self.cart_button = QPushButton("购物车")
        self.database_button = QPushButton("选择数据库")
        nav_layout.addWidget(self.inventory_button)
        nav_layout.addWidget(self.cart_button)
        nav_layout.addWidget(self.database_button)
        nav_layout.addStretch(1)

        self.stack = QStackedWidget()
        self.inventory_page = InventoryPage(database=self.database)
        self.cart_page = CartPage(database=self.database)
        self.stack.addWidget(self.inventory_page)
        self.stack.addWidget(self.cart_page)

        self.inventory_button.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.inventory_page)
        )
        self.cart_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.cart_page))
        self.database_button.clicked.connect(self._choose_database_file)

        layout.addLayout(nav_layout, 0)
        layout.addWidget(self.stack, 1)
        self.stack.setCurrentWidget(self.cart_page)

    def _choose_database_file(self) -> None:
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择数据库文件",
            str(self.database.path),
            "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*)",
        )
        if not selected_path:
            return

        new_path = Path(selected_path)
        if new_path == self.database.path:
            return

        try:
            new_database = Database(new_path)
            new_database.init_schema()
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"无法打开数据库文件：\n{exc}")
            return

        old_database = self.database
        self.database = new_database
        self.inventory_page.set_database(new_database)
        self.cart_page.set_database(new_database)
        old_database.close()
        QMessageBox.information(self, "成功", f"已切换数据库：\n{new_path}")
