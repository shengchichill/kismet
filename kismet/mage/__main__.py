import sys

from PyQt6.QtWidgets import QApplication

from kismet.mage.pet import MagePet


def main() -> None:
    try:
        app = QApplication(sys.argv)
    except Exception as exc:
        sys.exit(f"kismet.mage: cannot initialise Qt display: {exc}")

    app.setQuitOnLastWindowClosed(False)
    pet = MagePet()
    pet.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
