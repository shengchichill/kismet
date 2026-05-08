from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from kismet.presence import compute_mage_state, read_presence


class StateWatcher(QObject):
    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "idle"
        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def _poll(self) -> None:
        new_state = compute_mage_state(read_presence())
        if new_state != self._current:
            self._current = new_state
            self.state_changed.emit(new_state)
