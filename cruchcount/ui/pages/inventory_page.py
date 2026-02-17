from __future__ import annotations

from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cruchcount.db import Database


class InventoryPage(QWidget):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("请输入条码")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入商品名称")
        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setRange(0.01, 999999.99)
        self.price_input.setValue(1.0)
        self.price_input.setPrefix("¥")

        save_button = QPushButton("保存/入库")
        save_button.clicked.connect(self.save_product)

        form = QFormLayout()
        form.addRow("条码", self.barcode_input)
        form.addRow("商品名称", self.name_input)
        form.addRow("售价", self.price_input)

        group = QGroupBox("商品入库")
        group.setLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(save_button)

        self.hint_label = QLabel("规则：条码重复时将自动覆盖商品信息。")

        layout = QVBoxLayout(self)
        layout.addWidget(group)
        layout.addLayout(button_row)
        layout.addWidget(self.hint_label)
        layout.addStretch(1)

    def save_product(self) -> None:
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        price = float(self.price_input.value())

        if not barcode:
            QMessageBox.warning(self, "提示", "请输入条码")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入商品名称")
            return

        exists = self.database.get_product_by_barcode(barcode) is not None
        self.database.upsert_product(barcode=barcode, name=name, price=price)

        if exists:
            QMessageBox.information(self, "成功", "商品已覆盖更新")
        else:
            QMessageBox.information(self, "成功", "商品已新增入库")

        self.barcode_input.clear()
        self.name_input.clear()
        self.price_input.setValue(1.0)
        self.barcode_input.setFocus()
