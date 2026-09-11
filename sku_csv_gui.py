#!/usr/bin/env python3
"""
sku_csv_gui.py - Cross-platform (Linux/Windows) Qt GUI that builds SKU
combinations from a nested structure.

Requires PySide6:
    pip install PySide6

Usage:
    python3 sku_csv_gui.py        (Linux/macOS)
    python sku_csv_gui.py         (Windows)
"""

import csv
import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

HEADERS = ["skuBase", "skuColour", "skuSize", "skuFull", "checkedBy", "printTime"]


class ColourGroup(QFrame):
    """One Colour, with its own attached set of Size boxes."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._on_change = on_change

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        # Set top margin to 0 so skuColour aligns horizontally with skuBase
        layout.setContentsMargins(10, 0, 10, 10)

        # Left Column: Colour
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.addWidget(QLabel("skuColour:"))
        self.colour_edit = QLineEdit()
        self.colour_edit.textChanged.connect(self._on_change)
        left_layout.addWidget(self.colour_edit)
        layout.addLayout(left_layout, 1)

        # Right Column: Sizes (Balanced stretch factor to 1 for equal sizing)
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.addWidget(QLabel("skuSize & boxCount:"))
        
        self.size_box_holder = QWidget()
        self.size_layout = QVBoxLayout(self.size_box_holder)
        self.size_layout.setAlignment(Qt.AlignTop)
        self.size_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.size_box_holder)

        size_btn_row = QHBoxLayout()
        add_size_btn = QPushButton("+ Add Size")
        remove_size_btn = QPushButton("+ Remove Last Size")
        add_size_btn.clicked.connect(self.add_size_box)
        remove_size_btn.clicked.connect(self.remove_size_box)
        size_btn_row.addWidget(add_size_btn)
        size_btn_row.addWidget(remove_size_btn)
        right_layout.addLayout(size_btn_row)

        layout.addLayout(right_layout, 1)

        self.size_widgets = []
        self.add_size_box()

    def add_size_box(self):
        size_row_widget = QWidget()
        size_row_layout = QHBoxLayout(size_row_widget)
        size_row_layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit()
        edit.textChanged.connect(self._on_change)
        
        box_count_spin = QSpinBox()
        box_count_spin.setMinimum(1)
        box_count_spin.setValue(1)
        box_count_spin.valueChanged.connect(self._on_change)
        
        size_row_layout.addWidget(edit)
        size_row_layout.addWidget(QLabel("boxCount:"))
        size_row_layout.addWidget(box_count_spin)

        self.size_layout.addWidget(size_row_widget)
        self.size_widgets.append((size_row_widget, edit, box_count_spin))
        self._on_change()

    def remove_size_box(self):
        if len(self.size_widgets) <= 1:
            return
        size_row_widget, edit, box_count_spin = self.size_widgets.pop()
        size_row_widget.deleteLater()
        self._on_change()

    def colour_value(self):
        return self.colour_edit.text().strip().upper()

    def pairs(self):
        """List of (colour, size) tuples for this colour group, factoring in boxCount."""
        colour = self.colour_value()
        if not colour:
            return []
            
        results = []
        for _, edit, box_count_spin in self.size_widgets:
            size_val = edit.text().strip().upper()
            if size_val:
                count = box_count_spin.value()
                for _ in range(count):
                    results.append((colour, size_val))
                    
        return results


class BaseGroup(QFrame):
    """One Base, with its own attached set of Colour groups (each with its
    own Sizes). Adding a new Base starts with a fresh, empty set of colours.
    """

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._on_change = on_change
        self.colour_groups = []

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # Left Column: Base and checkedBy
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        
        left_layout.addWidget(QLabel("skuBase:"))
        self.base_edit = QLineEdit()
        self.base_edit.textChanged.connect(self._on_change)
        left_layout.addWidget(self.base_edit)
        
        left_layout.addWidget(QLabel("checkedBy:"))
        self.checked_edit = QLineEdit()
        self.checked_edit.textChanged.connect(self._on_change)
        left_layout.addWidget(self.checked_edit)
        
        layout.addLayout(left_layout, 1)

        # Right Column: Colours (double stretch: this side splits again into
        # Colour + Size at 1:1, so each ends up the same width as Base)
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        
        self.colours_container = QWidget()
        self.colours_layout = QVBoxLayout(self.colours_container)
        self.colours_layout.setAlignment(Qt.AlignTop)
        self.colours_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.colours_container)

        colour_btn_row = QHBoxLayout()
        colour_btn_row.setContentsMargins(10, 0, 0, 0)
        add_colour_btn = QPushButton("+ Add Colour")
        remove_colour_btn = QPushButton("+ Remove Last Colour")
        add_colour_btn.clicked.connect(self.add_colour_group)
        remove_colour_btn.clicked.connect(self.remove_colour_group)
        colour_btn_row.addWidget(add_colour_btn)
        colour_btn_row.addWidget(remove_colour_btn)
        colour_btn_row.addStretch()
        right_layout.addLayout(colour_btn_row)

        layout.addLayout(right_layout, 2)

        self.add_colour_group()

    def add_colour_group(self):
        group = ColourGroup(on_change=self._on_change)
        self.colour_groups.append(group)
        self.colours_layout.addWidget(group)
        self._on_change()

    def remove_colour_group(self):
        if len(self.colour_groups) <= 1:
            QMessageBox.information(
                self, "Can't remove", "Each Base group needs at least one Colour group."
            )
            return
        group = self.colour_groups.pop()
        group.deleteLater()
        self._on_change()

    def base_value(self):
        return self.base_edit.text().strip().upper()
        
    def checked_value(self):
        return self.checked_edit.text().strip()

    def rows(self):
        """List of (base, colour, size, sku, checkedBy) rows for this base group."""
        base = self.base_value()
        if not base:
            return []
            
        checked_by = self.checked_value()
        out = []
        for group in self.colour_groups:
            for colour, size in group.pairs():
                out.append((base, colour, size, f"{base}-{colour}-{size}", checked_by))
        return out


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SKU CSV Generator")
        # Set default size to 720p (1280x720)
        self.resize(1280, 720)

        self.queued_rows = []
        self.base_groups = []

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        intro = QLabel(
            "Each Base group has its own Colour groups, and each Colour "
            "group has its own Sizes. Nothing is shared between Base "
            "groups, and nothing is shared between Colour groups."
        )
        intro.setWordWrap(True)
        main_layout.addWidget(intro)

        main_layout.addWidget(QLabel("Base groups:"))
        self.bases_scroll = QScrollArea()
        self.bases_scroll.setWidgetResizable(True)
        self.bases_scroll.setMinimumHeight(300)
        self.bases_container = QWidget()
        self.bases_layout = QVBoxLayout(self.bases_container)
        self.bases_layout.setAlignment(Qt.AlignTop)
        self.bases_scroll.setWidget(self.bases_container)
        main_layout.addWidget(self.bases_scroll)

        base_btn_row = QHBoxLayout()
        add_base_btn = QPushButton("+ Add Base Group")
        remove_base_btn = QPushButton("+ Remove Last Base Group")
        add_base_btn.clicked.connect(self.add_base_group)
        remove_base_btn.clicked.connect(self.remove_last_base_group)
        base_btn_row.addWidget(add_base_btn)
        base_btn_row.addWidget(remove_base_btn)
        base_btn_row.addStretch()
        main_layout.addLayout(base_btn_row)

        empty_frame = QFrame()
        empty_frame.setFrameShape(QFrame.StyledPanel)
        empty_frame.setMinimumHeight(20)
        empty_frame.setMaximumHeight(20)
        main_layout.addWidget(empty_frame)

        preview_row = QHBoxLayout()
        self.preview_label = QLabel("This would add 0 row(s).")
        add_to_queue_btn = QPushButton("Add to Queue")
        add_to_queue_btn.clicked.connect(self.add_to_queue)
        preview_row.addWidget(self.preview_label)
        preview_row.addStretch()
        preview_row.addWidget(add_to_queue_btn)
        main_layout.addLayout(preview_row)

        main_layout.addWidget(QLabel("Queued rows:"))
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(150)
        main_layout.addWidget(self.queue_list)

        queue_btn_row = QHBoxLayout()
        clear_queue_btn = QPushButton("Clear Queue")
        clear_queue_btn.clicked.connect(self.clear_queue)
        save_btn = QPushButton("Save CSV\u2026")
        save_btn.clicked.connect(self.save_csv)
        queue_btn_row.addWidget(clear_queue_btn)
        queue_btn_row.addStretch()
        queue_btn_row.addWidget(save_btn)
        main_layout.addLayout(queue_btn_row)

        self.add_base_group()
        self.update_preview()

    def add_base_group(self):
        group = BaseGroup(on_change=self.update_preview)
        self.base_groups.append(group)
        self.bases_layout.addWidget(group)
        self.update_preview()

    def remove_last_base_group(self):
        if len(self.base_groups) <= 1:
            QMessageBox.information(
                self, "Can't remove", "At least one Base group is required."
            )
            return
        group = self.base_groups.pop()
        group.deleteLater()
        self.update_preview()

    def all_rows(self):
        rows = []
        for group in self.base_groups:
            rows.extend(group.rows())
        return rows

    def update_preview(self):
        total = len(self.all_rows())
        self.preview_label.setText(f"This would add {total} row(s).")

    def add_to_queue(self):
        new_rows = self.all_rows()
        if not new_rows:
            QMessageBox.warning(
                self,
                "Missing values",
                "Please fill in at least one Base, with at least one "
                "Colour, and at least one Size.",
            )
            return

        self.queued_rows.extend(new_rows)
        for row in new_rows:
            self.queue_list.addItem(", ".join(row))

    def clear_queue(self):
        self.queued_rows = []
        self.queue_list.clear()

    def save_csv(self):
        if not self.queued_rows:
            QMessageBox.information(
                self, "Nothing to save", "Add at least one group to the queue first."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "skus.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"

        try:
            current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            rows_with_timestamp = [list(row) + [current_time] for row in self.queued_rows]

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)
                writer.writerows(rows_with_timestamp)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save file:\n{exc}")
            return

        QMessageBox.information(
            self, "Saved", f"Saved {len(self.queued_rows)} row(s) to:\n{path}"
        )


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
