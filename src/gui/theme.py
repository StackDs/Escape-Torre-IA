"""Estilos y paleta de colores para la GUI de Escape de la Torre IA."""

TEMA_OSCURO = """
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #0f172a;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QGroupBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 10px 8px 10px;
    font-weight: 600;
    color: #e2e8f0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #60a5fa;
}

QLabel {
    color: #cbd5e1;
}

QLabel[heading="true"] {
    font-size: 18px;
    font-weight: bold;
    color: #f8fafc;
}

QLabel[badge="true"] {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    color: #93c5fd;
}

QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}

QPushButton[variant="success"] {
    background-color: #10b981;
}
QPushButton[variant="success"]:hover {
    background-color: #059669;
}
QPushButton[variant="success"]:pressed {
    background-color: #047857;
}

QPushButton[variant="danger"] {
    background-color: #ef4444;
}
QPushButton[variant="danger"]:hover {
    background-color: #dc2626;
}
QPushButton[variant="danger"]:pressed {
    background-color: #b91c1c;
}

QPushButton[variant="warning"] {
    background-color: #f59e0b;
    color: #0f172a;
}
QPushButton[variant="warning"]:hover {
    background-color: #d97706;
}
QPushButton[variant="warning"]:pressed {
    background-color: #b45309;
}

QPushButton[variant="secondary"] {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
}
QPushButton[variant="secondary"]:hover {
    background-color: #475569;
}
QPushButton[variant="secondary"]:pressed {
    background-color: #1e293b;
}

QTabWidget::pane {
    border: 1px solid #334155;
    background-color: transparent;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 10px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 11.5px;
}

QTabBar::tab:hover {
    background-color: #27354f;
    color: #f1f5f9;
}

QTabBar::tab:selected {
    background-color: #0f172a;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}

QTabBar::tab:!selected {
    margin-top: 2px;
}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 22px;
    color: #f8fafc;
    selection-background-color: #3b82f6;
}

QSpinBox, QDoubleSpinBox {
    padding-right: 20px;
}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
    border: 1px solid #60a5fa;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #475569;
    selection-background-color: #3b82f6;
    color: #f8fafc;
    padding: 4px;
}

QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 5px;
}

QPlainTextEdit, QTextEdit {
    background-color: #090d16;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #a7f3d0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 6px;
}

QScrollBar:vertical {
    border: none;
    background-color: #0f172a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #0f172a;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #334155;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #60a5fa;
    border: 1px solid #3b82f6;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #93c5fd;
}
"""

def aplicar_tema(app):
    """Aplica la hoja de estilos global a la aplicación QApplication."""
    app.setStyleSheet(TEMA_OSCURO)
