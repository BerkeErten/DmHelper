"""Jump Rule calculator UI (live-updating).

Jump calculator method and UI logic based on Fexlabs.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QFrame,
)
from PyQt6.QtCore import Qt

from core.dnd_utils import calculate_jump_distance_us

_LABEL = "color: #94a3b8; font-size: 11px;"
_HEADER = "color: #E2E8F0; font-size: 12px; font-weight: 600;"
_RESULT = "color: #f97316; font-size: 12px; font-weight: 600;"
_DIVIDER_STYLE = "background-color: #3c3c3c; max-height: 1px;"
_INPUT_STYLE = """
QSpinBox {
    background-color: #1e1e1e;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #E2E8F0;
    padding: 4px 8px;
    min-width: 52px;
}
"""


class _ToggleRow(QWidget):
    """Checkbox row with rich-text label (bold prefix)."""

    def __init__(self, label_html: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.cb = QCheckBox()
        self.cb.setStyleSheet("color: #E2E8F0;")
        row.addWidget(self.cb, 0, Qt.AlignmentFlag.AlignTop)

        lbl = QLabel(label_html)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        row.addWidget(lbl, 1)

        # Make label clickable to toggle checkbox
        lbl.mousePressEvent = lambda e: self.cb.toggle()


class JumpCalculatorWidget(QWidget):
    """Inputs + toggles + live results, similar to the reference layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._setup_ui()
        self._connect_signals()
        self._calculate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hint = QLabel("This calculator uses the jumping rules found in the 5th Edition Player's Handbook.")
        hint.setStyleSheet(_LABEL)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        top = QHBoxLayout()
        top.setSpacing(18)

        def _lbl(t: str) -> QLabel:
            l = QLabel(t)
            l.setStyleSheet(_HEADER)
            l.setWordWrap(True)
            return l

        # Left: inputs
        left = QVBoxLayout()
        left.setSpacing(8)

        left.addWidget(_lbl("What is your Strength score?"))
        self.str_spin = QSpinBox()
        self.str_spin.setRange(1, 30)
        self.str_spin.setValue(18)
        self.str_spin.setStyleSheet(_INPUT_STYLE)
        left.addWidget(self.str_spin, 0, Qt.AlignmentFlag.AlignLeft)

        left.addWidget(_lbl("What is your Dexterity score?"))
        self.dex_spin = QSpinBox()
        self.dex_spin.setRange(1, 30)
        self.dex_spin.setValue(14)
        self.dex_spin.setStyleSheet(_INPUT_STYLE)
        left.addWidget(self.dex_spin, 0, Qt.AlignmentFlag.AlignLeft)

        left.addWidget(_lbl("How tall are you?"))
        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        self.feet_spin = QSpinBox()
        self.feet_spin.setRange(0, 12)
        self.feet_spin.setValue(6)
        self.feet_spin.setStyleSheet(_INPUT_STYLE)
        hrow.addWidget(self.feet_spin)
        ft = QLabel("feet")
        ft.setStyleSheet(_LABEL)
        hrow.addWidget(ft)
        self.inches_spin = QSpinBox()
        self.inches_spin.setRange(0, 11)
        self.inches_spin.setValue(0)
        self.inches_spin.setStyleSheet(_INPUT_STYLE)
        hrow.addWidget(self.inches_spin)
        inch = QLabel("inches")
        inch.setStyleSheet(_LABEL)
        hrow.addWidget(inch)
        hrow.addStretch()
        left.addLayout(hrow)

        top.addLayout(left, 1)

        # Right: toggle list (like screenshot)
        right = QVBoxLayout()
        right.setSpacing(6)

        self.row_tiger = _ToggleRow("<b>Barbarian</b> - Totem Spirit: Tiger")
        self.row_remarkable = _ToggleRow("<b>Fighter</b> - Champion: Remarkable Athlete")
        self.row_step = _ToggleRow("<b>Monk</b> - Step of the Wind")
        self.row_second = _ToggleRow("<b>Rogue</b> - Thief: Second Story Work")
        self.row_jump = _ToggleRow("<b>Spell</b> - Jump")
        self.row_athlete = _ToggleRow("<b>Feat</b> - Athlete")
        self.row_boots = _ToggleRow("<b>Magic Item</b> - Boots of Striding and Springing")

        for w in (
            self.row_tiger,
            self.row_remarkable,
            self.row_step,
            self.row_second,
            self.row_jump,
            self.row_athlete,
            self.row_boots,
        ):
            right.addWidget(w)
        right.addStretch()
        top.addLayout(right, 1)

        layout.addLayout(top)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(_DIVIDER_STYLE)
        layout.addWidget(div)

        # Results
        run_header = QLabel("With a running start…")
        run_header.setStyleSheet(_HEADER)
        layout.addWidget(run_header)
        self.run_hint = QLabel("(10 feet of movement)")
        self.run_hint.setStyleSheet(_LABEL)
        layout.addWidget(self.run_hint)

        self.run_long = QLabel("—")
        self.run_long.setStyleSheet(_RESULT)
        layout.addWidget(self.run_long)
        self.run_high = QLabel("—")
        self.run_high.setStyleSheet(_RESULT)
        layout.addWidget(self.run_high)
        self.run_grab = QLabel("—")
        self.run_grab.setStyleSheet(_RESULT)
        layout.addWidget(self.run_grab)

        layout.addSpacing(8)

        stand_header = QLabel("Without a running start…")
        stand_header.setStyleSheet(_HEADER)
        layout.addWidget(stand_header)

        self.stand_long = QLabel("—")
        self.stand_long.setStyleSheet(_RESULT)
        layout.addWidget(self.stand_long)
        self.stand_high = QLabel("—")
        self.stand_high.setStyleSheet(_RESULT)
        layout.addWidget(self.stand_high)
        self.stand_grab = QLabel("—")
        self.stand_grab.setStyleSheet(_RESULT)
        layout.addWidget(self.stand_grab)

    def _connect_signals(self):
        self.str_spin.valueChanged.connect(self._calculate)
        self.dex_spin.valueChanged.connect(self._calculate)
        self.feet_spin.valueChanged.connect(self._calculate)
        self.inches_spin.valueChanged.connect(self._calculate)
        for row in (
            self.row_tiger,
            self.row_remarkable,
            self.row_step,
            self.row_second,
            self.row_jump,
            self.row_athlete,
            self.row_boots,
        ):
            row.cb.stateChanged.connect(self._calculate)

    def _calculate(self):
        out = calculate_jump_distance_us(
            self.str_spin.value(),
            self.dex_spin.value(),
            self.feet_spin.value(),
            self.inches_spin.value(),
            is_tiger_barbarian=self.row_tiger.cb.isChecked(),
            is_remarkable_athlete=self.row_remarkable.cb.isChecked(),
            is_step_of_the_wind=self.row_step.cb.isChecked(),
            is_second_story=self.row_second.cb.isChecked(),
            is_jump_spell=self.row_jump.cb.isChecked(),
            is_athlete_feat=self.row_athlete.cb.isChecked(),
            is_boots_of_striding_and_spring=self.row_boots.cb.isChecked(),
        )
        self.run_long.setText(f"…your long jump is <b>{int(out['run_horizontal'])}</b> feet horizontally.")
        self.run_high.setText(f"…your high jump is <b>{int(out['run_vertical'])}</b> feet off the ground.")
        self.run_grab.setText(f"…you can reach up and grab something <b>{out['run_grab']:.1f}</b> feet off the ground.")

        self.stand_long.setText(f"…your long jump is <b>{int(out['stand_horizontal'])}</b> feet horizontally.")
        self.stand_high.setText(f"…your high jump is <b>{int(out['stand_vertical'])}</b> feet off the ground.")
        self.stand_grab.setText(f"…you can reach up and grab something <b>{out['stand_grab']:.1f}</b> feet off the ground.")

        # Athlete feat: 5 ft run-up when on, 10 ft when off
        self.run_hint.setText("(5 feet of movement)" if self.row_athlete.cb.isChecked() else "(10 feet of movement)")

