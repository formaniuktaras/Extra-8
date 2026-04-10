from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Про програму")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("DOCX Indexer UA\nВерсія 1.0"))
