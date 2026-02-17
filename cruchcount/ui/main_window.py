from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
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
        self.resize(980, 640)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        nav_layout = QVBoxLayout()
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.inventory_button = QPushButton("入库")
        self.cart_button = QPushButton("购物车")
        nav_layout.addWidget(self.inventory_button)
        nav_layout.addWidget(self.cart_button)
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

        layout.addLayout(nav_layout, 0)
        layout.addWidget(self.stack, 1)
        self.stack.setCurrentWidget(self.cart_page)
