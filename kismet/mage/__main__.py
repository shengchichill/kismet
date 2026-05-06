import os
import sys

from PyQt6.QtWidgets import QApplication

from kismet.mage.pet import MagePet
from kismet.presence import MAGE_PID_FILE


def main() -> None:
    try:
        app = QApplication(sys.argv)
    except Exception as exc:
        sys.exit(f"kismet.mage: cannot initialise Qt display: {exc}")

    MAGE_PID_FILE.write_text(str(os.getpid()))
    app.setQuitOnLastWindowClosed(False)
    pet = MagePet()
    pet.show()
    exit_code = app.exec()
    MAGE_PID_FILE.unlink(missing_ok=True)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
