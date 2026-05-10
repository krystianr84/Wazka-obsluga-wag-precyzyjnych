import sys
import os

# Zapewnia poprawne importy zarówno przy uruchomieniu przez Python jak i z exe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from services.app_settings_service import AppSettingsService
from ui.theme import ThemeManager
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    settings_service = AppSettingsService()
    ThemeManager.initialize(settings_service.theme)
    app.setPalette(ThemeManager.instance().build_initial_palette())

    window = MainWindow(settings_service)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
