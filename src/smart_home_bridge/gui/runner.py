import sys

from loxone_bridge.config import load_config
from loxone_bridge.gui.factory import create_gui_bridge_context
from loxone_bridge.services import EnvSettingsService


def run():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise SystemExit(
            'PySide6 is required for the GUI. Install it with: pip install -e ".[gui]"'
        ) from exc

    from loxone_bridge.gui.main_window import MainWindow

    env_settings = EnvSettingsService()
    qt_app = QApplication(sys.argv)
    window = MainWindow(create_gui_bridge_context(load_config(), env_settings))
    window.show()
    sys.exit(qt_app.exec())
