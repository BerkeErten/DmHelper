"""Placeholder content for the Display Menu when no item is selected."""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

# Match app dark theme
_BG = "#2b2b2b"
_TITLE_STYLE = "color: #E2E8F0; font-size: 14px; font-weight: 600;"
_SUBTITLE_STYLE = "color: #94a3b8; font-size: 12px;"
_CARD_STYLE = """
QFrame#DisplayMenuCard {
    background-color: #2f2f2f;
    border: 1px solid #3c3c3c;
    border-radius: 10px;
}
QFrame#DisplayMenuCard:hover {
    background-color: #353535;
    border: 1px solid #4c4c4c;
}
"""
_DIVIDER_STYLE = "background-color: #3c3c3c; max-height: 1px;"
_SECTION_HEADING_STYLE = "color: #E2E8F0; font-size: 12px; font-weight: 600;"
_TOGGLE_LIST_STYLE = """
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 6px 0;
    color: #E2E8F0;
}
"""


def _rules_content_widget() -> QWidget:
    """Build Rules card expand content: Official Rules <divider> list, Homebrew Rules <divider> list."""
    from ui.display_menu.jump_calculator_widget import JumpCalculatorWidget

    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(14, 8, 14, 12)
    layout.setSpacing(12)

    def _section(title: str, items: list[str], *, allow_jump_expand: bool = False) -> None:
        heading = QLabel(title)
        heading.setStyleSheet(_SECTION_HEADING_STYLE)
        layout.addWidget(heading)
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(_DIVIDER_STYLE)
        layout.addWidget(div)
        # We render items as a vertical list of checkboxes, optionally expanding Jump Rule into a calculator panel.
        list_container = QWidget()
        list_container.setStyleSheet("background: transparent;")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)

        for label in items:
            cb = QCheckBox(label)
            cb.setStyleSheet("color: #E2E8F0; font-size: 12px;")
            list_layout.addWidget(cb)

            if allow_jump_expand and label.lower() == "jump rule":
                calc = JumpCalculatorWidget()
                calc.setVisible(False)
                list_layout.addWidget(calc)
                cb.toggled.connect(calc.setVisible)

        layout.addWidget(list_container)

    _section("Official Rules", ["Jump Rule"], allow_jump_expand=True)
    _section("Homebrew Rules", ["Crit Table", "Exploding Dice"])
    return container


class ExpandableCard(QFrame):
    """Card that expands on click to show a divider and either custom content or a toggle list."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_text: str,
        toggles: list[str] | None = None,
        custom_expand_widget: QWidget | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DisplayMenuCard")
        self.setStyleSheet(_CARD_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expanded = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header row (always visible, clickable)
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        row = QHBoxLayout(header)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        icon = QLabel(icon_text)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(36, 36)
        icon.setStyleSheet(
            "background-color: #2f2f2f; border: 1px solid #3c3c3c; "
            "border-radius: 8px; color: #E2E8F0; font-size: 16px;"
        )
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QWidget()
        text_col.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(_TITLE_STYLE)
        t.setWordWrap(True)
        text_layout.addWidget(t)
        d = QLabel(subtitle)
        d.setStyleSheet(_SUBTITLE_STYLE)
        d.setWordWrap(True)
        text_layout.addWidget(d)
        row.addWidget(text_col, 1)
        for w in (header, icon, text_col, t, d):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        main_layout.addWidget(header)

        # Expandable area: divider + content (custom widget or toggle list)
        self._divider = QFrame()
        self._divider.setFixedHeight(1)
        self._divider.setStyleSheet(_DIVIDER_STYLE)
        self._divider.setVisible(False)
        main_layout.addWidget(self._divider)

        if custom_expand_widget is not None:
            custom_expand_widget.setVisible(False)
            self._expandable = custom_expand_widget
            self._toggle_list = None
        else:
            toggle_container = QWidget()
            toggle_container.setStyleSheet("background: transparent;")
            toggle_layout = QVBoxLayout(toggle_container)
            toggle_layout.setContentsMargins(14, 8, 14, 12)
            toggle_layout.setSpacing(0)
            self._toggle_list = QListWidget()
            self._toggle_list.setStyleSheet(_TOGGLE_LIST_STYLE)
            self._toggle_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            toggle_labels = toggles if toggles is not None else [f"Placeholder item {i + 1}" for i in range(3)]
            for label in toggle_labels:
                item = QListWidgetItem()
                cb = QCheckBox(label)
                cb.setStyleSheet("color: #E2E8F0; font-size: 12px;")
                self._toggle_list.addItem(item)
                self._toggle_list.setItemWidget(item, cb)
            self._toggle_list.setVisible(False)
            toggle_layout.addWidget(self._toggle_list)
            self._expandable = toggle_container
        self._expandable.setVisible(False)
        main_layout.addWidget(self._expandable)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_expand()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._divider.setVisible(self._expanded)
        self._expandable.setVisible(self._expanded)
        if self._toggle_list is not None:
            self._toggle_list.setVisible(self._expanded)


class PlaceholderDisplayWidget(QWidget):
    """Scrollable empty state with card-like placeholders."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _make_card(
        self,
        title: str,
        subtitle: str,
        icon_text: str,
        toggles: list[str] | None = None,
        custom_expand_widget: QWidget | None = None,
    ) -> ExpandableCard:
        return ExpandableCard(
            title, subtitle, icon_text,
            toggles=toggles,
            custom_expand_widget=custom_expand_widget,
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {_BG}; border: none; }} "
            f"QScrollArea > QWidget > QWidget {{ background-color: {_BG}; }}"
        )

        inner = QWidget()
        inner.setStyleSheet(f"background-color: {_BG};")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(24, 24, 24, 24)
        inner_layout.setSpacing(12)

        header = QLabel("Select an item to display")
        header.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header.setWordWrap(True)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        inner_layout.addWidget(header)

        inner_layout.addWidget(
            self._make_card(
                "Rules",
                "Official and homebrew rules.",
                "📜",
                custom_expand_widget=_rules_content_widget(),
            )
        )
        inner_layout.addWidget(
            self._make_card(
                "Lore & Story",
                "Select a lore entry to read it here.",
                "📖",
            )
        )
        inner_layout.addWidget(
            self._make_card(
                "Knowledge Base",
                "Open a knowledge entry to display it here.",
                "📚",
            )
        )
        inner_layout.addWidget(
            self._make_card(
                "Recent Notes",
                "Your latest notes will appear here as cards.",
                "🗒️",
            )
        )
        inner_layout.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        self.setMinimumWidth(200)
