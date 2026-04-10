from PySide6.QtWidgets import QTextEdit


class PreviewPanel(QTextEdit):
    def __init__(self, title: str = "") -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setPlaceholderText(title)
