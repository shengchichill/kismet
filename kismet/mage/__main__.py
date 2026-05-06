import sys

from PyQt6.QtWidgets import QApplication

from kismet.mage.pet import MagePet


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = MagePet()
    pet.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
