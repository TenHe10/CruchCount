from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from PyQt6.QtCore import QStringListModel, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cruchcount.db import Database


@dataclass
class CartItem:
    barcode: str
    name: str
    price: float
    quantity: int

    @property
    def subtotal(self) -> float:
        return self.price * self.quantity


class UnknownProductDialog(QDialog):
    def __init__(self, barcode: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("该商品未入库")
        self.barcode = barcode

        self.price_input = QDoubleSpinBox()
        self.price_input.setDecimals(2)
        self.price_input.setRange(0.01, 999999.99)
        self.price_input.setValue(1.0)
        self.price_input.setPrefix("¥")

        form = QFormLayout()
        form.addRow("条码", QLabel(barcode))
        form.addRow("临时售价", self.price_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认加入")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def selected_price(self) -> float:
        return float(self.price_input.value())


class CartPage(QWidget):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.cart_items: dict[str, CartItem] = {}
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("扫码枪输入后回车，支持连续扫码")
        self.scan_input.returnPressed.connect(self._on_scan_submitted)

        self.manual_combo = QComboBox()
        self.manual_combo.setEditable(True)
        self.manual_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.manual_combo.lineEdit().setPlaceholderText("手动输入条码（支持联想）")
        self.manual_combo.lineEdit().textEdited.connect(self._update_suggestions)
        self.manual_combo.lineEdit().returnPressed.connect(self._on_manual_submitted)

        self.completer_model = QStringListModel()
        completer = QCompleter(self.completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.manual_combo.setCompleter(completer)

        add_manual_button = QPushButton("手动加入")
        add_manual_button.clicked.connect(self._on_manual_submitted)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["条码", "商品", "单价", "数量", "小计", "操作"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellChanged.connect(self._on_cell_changed)

        self.total_qty_label = QLabel("总件数：0")
        self.total_amount_label = QLabel("总金额：¥0.00")
        checkout_button = QPushButton("结账")
        checkout_button.clicked.connect(self._checkout)
        clear_button = QPushButton("清空购物车")
        clear_button.clicked.connect(self._clear_cart)

        input_group = QGroupBox("加入购物车")
        input_layout = QFormLayout()
        input_layout.addRow("扫码输入", self.scan_input)
        manual_row = QHBoxLayout()
        manual_row.addWidget(self.manual_combo, 1)
        manual_row.addWidget(add_manual_button)
        input_layout.addRow("手动输入", manual_row)
        input_group.setLayout(input_layout)

        footer = QHBoxLayout()
        footer.addWidget(self.total_qty_label)
        footer.addWidget(self.total_amount_label)
        footer.addStretch(1)
        footer.addWidget(checkout_button)
        footer.addWidget(clear_button)

        layout = QVBoxLayout(self)
        layout.addWidget(input_group)
        layout.addWidget(self.table)
        layout.addLayout(footer)

        self._update_suggestions("")
        self.scan_input.setFocus()

    def _on_scan_submitted(self) -> None:
        barcode = self.scan_input.text().strip()
        self.scan_input.clear()
        if not barcode:
            return
        self._add_by_barcode(barcode)
        self.scan_input.setFocus()

    def _on_manual_submitted(self) -> None:
        text = self.manual_combo.currentText().strip()
        if not text:
            return
        barcode = text.split(" | ", 1)[0].strip()
        self._add_by_barcode(barcode)
        self.manual_combo.lineEdit().clear()
        self._update_suggestions("")
        self.scan_input.setFocus()

    def _update_suggestions(self, query: str) -> None:
        products = self.database.search_products(query, limit=20)
        display_items = [
            f"{item['barcode']} | {item['name']} | ¥{item['price']:.2f}" for item in products
        ]
        self.completer_model.setStringList(display_items)
        self.manual_combo.clear()
        self.manual_combo.addItems(display_items)
        self.manual_combo.setEditText(query)

    def _add_by_barcode(self, barcode: str) -> None:
        product = self.database.get_product_by_barcode(barcode)
        if product is None:
            product = self._resolve_unknown_product(barcode)
            if product is None:
                return

        if barcode in self.cart_items:
            self.cart_items[barcode].quantity += 1
        else:
            self.cart_items[barcode] = CartItem(
                barcode=barcode,
                name=str(product["name"]),
                price=float(product["price"]),
                quantity=1,
            )
        self._render_table()

    def _resolve_unknown_product(self, barcode: str) -> dict[str, str | float] | None:
        dialog = UnknownProductDialog(barcode=barcode, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return {
            "barcode": barcode,
            "name": f"临时商品-{barcode[-4:] if len(barcode) >= 4 else barcode}",
            "price": dialog.selected_price,
        }

    def _render_table(self) -> None:
        items = list(self.cart_items.values())
        self.table.blockSignals(True)
        self.table.setRowCount(len(items))

        total_qty = 0
        total_amount = 0.0
        for row, item in enumerate(items):
            total_qty += item.quantity
            total_amount += item.subtotal

            barcode_item = QTableWidgetItem(item.barcode)
            name_item = QTableWidgetItem(item.name)
            price_item = QTableWidgetItem(f"¥{item.price:.2f}")
            quantity_item = QTableWidgetItem(str(item.quantity))
            subtotal_item = QTableWidgetItem(f"¥{item.subtotal:.2f}")

            barcode_item.setFlags(barcode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            price_item.setFlags(price_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            quantity_item.setFlags(
                quantity_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled
            )

            self.table.setItem(row, 0, barcode_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, price_item)
            self.table.setItem(row, 3, quantity_item)
            self.table.setItem(row, 4, subtotal_item)

            remove_button = QPushButton("移除")
            remove_button.clicked.connect(partial(self._remove_item_by_barcode, item.barcode))
            self.table.setCellWidget(row, 5, remove_button)

        self.total_qty_label.setText(f"总件数：{total_qty}")
        self.total_amount_label.setText(f"总金额：¥{total_amount:.2f}")
        self.table.blockSignals(False)

    def _clear_cart(self) -> None:
        if not self.cart_items:
            return
        answer = QMessageBox.question(self, "确认", "确定要清空购物车吗？")
        if answer == QMessageBox.StandardButton.Yes:
            self.cart_items.clear()
            self._render_table()
            self.scan_input.setFocus()

    def _remove_item_by_barcode(self, barcode: str) -> None:
        if barcode in self.cart_items:
            del self.cart_items[barcode]
            self._render_table()
        self.scan_input.setFocus()

    def _on_cell_changed(self, row: int, column: int) -> None:
        if column != 3:
            return

        barcode_item = self.table.item(row, 0)
        quantity_item = self.table.item(row, 3)
        if barcode_item is None or quantity_item is None:
            return

        barcode = barcode_item.text()
        cart_item = self.cart_items.get(barcode)
        if cart_item is None:
            return

        text = quantity_item.text().strip()
        try:
            quantity = int(text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "提示", "数量必须是大于 0 的整数")
            self._render_table()
            return

        cart_item.quantity = quantity
        self._render_table()

    def _checkout(self) -> None:
        if not self.cart_items:
            QMessageBox.information(self, "提示", "购物车为空，无法结账")
            return

        total_qty = sum(item.quantity for item in self.cart_items.values())
        total_amount = sum(item.subtotal for item in self.cart_items.values())
        answer = QMessageBox.question(
            self,
            "确认结账",
            f"共 {total_qty} 件，合计 ¥{total_amount:.2f}。\n确认结账吗？",
        )
        if answer == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "结账完成", f"实收金额：¥{total_amount:.2f}")
            self.cart_items.clear()
            self._render_table()
            self.scan_input.setFocus()
