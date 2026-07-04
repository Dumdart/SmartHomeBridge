APP_STYLESHEET = """
QMainWindow,
QScrollArea,
QWidget {
    background: #0b1220;
    color: #e5e7eb;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}

QScrollArea {
    border: none;
}

QFrame#statusStrip,
QFrame#operatorPanel,
QFrame#threatPanel,
QFrame#diagnosticsPanel,
QFrame#environmentPanel,
QFrame#activityPanel {
    background: #121c2d;
    border: 1px solid #263348;
    border-radius: 8px;
}

QFrame#statusCard,
QFrame#controlSurface,
QFrame#detailSurface {
    background: #0f172a;
    border: 1px solid #243149;
    border-radius: 8px;
}

QLabel#appTitle {
    color: #f9fafb;
    font-size: 22px;
    font-weight: 700;
}

QLabel#appSubtitle,
QLabel#sectionCaption,
QLabel#mutedText {
    color: #9ca3af;
}

QLabel#panelTitle {
    color: #f9fafb;
    font-size: 15px;
    font-weight: 700;
}

QLabel#statusLabel,
QLabel#detailLabel,
QLabel#fieldLabel {
    color: #9ca3af;
    font-size: 12px;
    font-weight: 600;
}

QLabel#detailValue,
QLabel#metricValue {
    color: #f3f4f6;
}

QLabel#doorStateValue,
QLabel#doorPanelStateValue,
QLabel#threatLevelValue,
QLabel#statusValue,
QLabel#cameraHealthValue,
QLabel#statusStripCameraValue {
    border-radius: 6px;
    font-weight: 700;
    padding: 6px 10px;
}

QLabel[tone="good"] {
    background: #12402d;
    color: #bbf7d0;
}

QLabel[tone="notice"] {
    background: #133a5f;
    color: #bfdbfe;
}

QLabel[tone="neutral"] {
    background: #263348;
    color: #d1d5db;
}

QLabel[tone="warning"] {
    background: #4a3414;
    color: #fde68a;
}

QLabel[tone="danger"] {
    background: #4c1717;
    color: #fecaca;
}

QLabel[tone="working"] {
    background: #1e3a5f;
    color: #dbeafe;
}

QLineEdit,
QSpinBox,
QTextEdit {
    background: #0b1220;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #f9fafb;
    padding: 7px 9px;
}

QLineEdit:focus,
QSpinBox:focus,
QTextEdit:focus {
    border-color: #38bdf8;
}

QPushButton {
    background: #243149;
    border: 1px solid #3b4a64;
    border-radius: 6px;
    color: #f9fafb;
    font-weight: 700;
    padding: 8px 14px;
}

QPushButton:hover {
    background: #304057;
}

QPushButton#primaryButton {
    background: #1d4ed8;
    border-color: #2563eb;
}

QPushButton#primaryButton:hover {
    background: #2563eb;
}

QPushButton#warningButton {
    background: #92400e;
    border-color: #b45309;
}

QPushButton#warningButton:hover {
    background: #a34d10;
}

QPushButton#dangerButton {
    background: #991b1b;
    border-color: #b91c1c;
}

QPushButton#dangerButton:hover {
    background: #b91c1c;
}

QLabel#inferenceImage {
    background: #050816;
    border: 1px solid #263348;
    border-radius: 8px;
    color: #9ca3af;
}

QTextEdit#activityLog {
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 13px;
}

QProgressBar {
    background: #0b1220;
    border: 1px solid #334155;
    border-radius: 4px;
    height: 8px;
}

QProgressBar::chunk {
    background: #38bdf8;
    border-radius: 4px;
}
"""
