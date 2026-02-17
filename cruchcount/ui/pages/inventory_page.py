from __future__ import annotations

from PyQt6.QtCore import QStringListModel, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
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

        self.barcode_combo = QComboBox()
        self.barcode_combo.setEditable(True)
        self.barcode_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.barcode_combo.lineEdit().setPlaceholderText("请输入条码（支持联想下拉）")
        self.barcode_combo.lineEdit().textEdited.connect(self._update_barcode_suggestions)
        self.barcode_combo.lineEdit().editingFinished.connect(
            self._on_barcode_editing_finished
        )

        self.barcode_completer_model = QStringListModel()
        barcode_completer = QCompleter(self.barcode_completer_model, self)
        barcode_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        barcode_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.barcode_combo.setCompleter(barcode_completer)

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
        form.addRow("条码", self.barcode_combo)
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

        self._update_barcode_suggestions("")

    def save_product(self) -> None:
        barcode = self.barcode_combo.currentText().strip().split(" | ", 1)[0].strip()
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

        self.barcode_combo.lineEdit().clear()
        self.name_input.clear()
        self.price_input.setValue(1.0)
        self._update_barcode_suggestions("")
        self.barcode_combo.setFocus()

    def _update_barcode_suggestions(self, query: str) -> None:
        products = self.database.search_products(query, limit=20)
        display_items = [
            f"{item['barcode']} | {item['name']} | ¥{item['price']:.2f}" for item in products
        ]
        self.barcode_completer_model.setStringList(display_items)
        self.barcode_combo.clear()
        self.barcode_combo.addItems(display_items)
        self.barcode_combo.setEditText(query)

    def _on_barcode_editing_finished(self) -> None:
        text = self.barcode_combo.currentText().strip()
        if not text:
            return

        barcode = text.split(" | ", 1)[0].strip()
        product = self.database.get_product_by_barcode(barcode)
        self.barcode_combo.setEditText(barcode)
        if product is None:
            return
        self.name_input.setText(str(product["name"]))
        self.price_input.setValue(float(product["price"]))
