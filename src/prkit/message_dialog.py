"""Compact, branded dialogs for startup messages."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from prkit.language import tr


class MessageDialog(QDialog):
    def __init__(
        self, app: QApplication, icon: QMessageBox.Icon, language: str, message: str
    ) -> None:
        super().__init__()
        self.setObjectName("prkitMessageDialog")
        self.setWindowTitle(tr("簡報瑞士刀", language))
        self.setWindowIcon(app.windowIcon())
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        critical = icon == QMessageBox.Icon.Critical
        self.badge = QLabel("!" if critical else "i", self)
        self.badge.setObjectName("statusBadge")
        self.badge.setFixedSize(20, 20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel(message, self)
        self.message_label.setObjectName("messageText")
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(360)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        content.addWidget(self.message_label, 1, Qt.AlignmentFlag.AlignVCenter)

        self.confirm_button = QPushButton(tr("確定", language), self)
        self.confirm_button.setObjectName("confirmButton")
        self.confirm_button.setFixedSize(76, 32)
        self.confirm_button.setDefault(True)
        self.confirm_button.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.confirm_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(22)
        layout.addLayout(content)
        layout.addLayout(actions)

        badge_color = "#D64545" if critical else "#2563EB"
        self.setStyleSheet(
            "QDialog#prkitMessageDialog { background-color: #FFFFFF; }"
            "QLabel#statusBadge { background-color: "
            f"{badge_color}; color: #FFFFFF; border-radius: 10px; "
            "font-size: 12px; font-weight: 600; }"
            "QLabel#messageText { color: #263445; font-size: 13px; }"
            "QPushButton#confirmButton { background-color: #2563EB; color: #FFFFFF; "
            "border: 0; border-radius: 6px; font-size: 13px; }"
            "QPushButton#confirmButton:hover { background-color: #1D4ED8; }"
            "QPushButton#confirmButton:pressed { background-color: #1E40AF; }"
        )
        self.ensurePolished()
        self.message_label.ensurePolished()
        text_width = self.message_label.fontMetrics().horizontalAdvance(message)
        margins = layout.contentsMargins()
        non_text_width = margins.left() + self.badge.width() + content.spacing() + margins.right()
        width = min(420, max(240, text_width + non_text_width))
        text_height = self.message_label.heightForWidth(width - non_text_width)
        height = (
            margins.top()
            + max(self.badge.height(), text_height)
            + layout.spacing()
            + self.confirm_button.height()
            + margins.bottom()
        )
        self.setFixedSize(width, height)
