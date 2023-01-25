import sgtk
import time
from sgtk.platform.qt import QtCore, QtGui


class TimeLordSignaller(QtCore.QObject):
    """
    Create signaller class for Sync Worker, required for using signals due to QObject inheritance
    """

    update_ui = QtCore.Signal(str)


class TimeLord(QtCore.QRunnable):
    def __init__(self):
        """
        Handles syncing specific file from perforce depot to local workspace on disk
        """
        super(TimeLord, self).__init__()
        self.signaller = TimeLordSignaller()

        # use signals from Signaller, since we cant in a non-QObject derrived
        # object like this QRunner.
        self.update_ui = self.signaller.update_ui

    @QtCore.Slot()
    def run(self):
        while True:
            time.sleep(2)
            self.update_ui.emit("model_view_update")
