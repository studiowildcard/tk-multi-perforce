from sgtk.platform.qt import QtCore, QtGui


class IconManager:
    def __init__(self, icon_finder):
        self.item = None
        self.col = 0
        self.icon_finder = icon_finder

        self._icons = {}

    def _setup_icon(self, icon):
        return icon.scaled(
            QtCore.QSize(23, 23),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )

    def _save_icon(self, path):
        if path not in self._icons:
            self._icons[path] = self._setup_icon(QtGui.QPixmap(path))
        return self._icons[path]

    @property
    def current_data(self):
        return self.item.data(self.col)

    def get_icon(self, name):
        icon_path = self.icon_finder(name)
        pix = self._save_icon(icon_path)
        return pix

    # dynamic returns used in schemas
    def sync_status(self):
        if hasattr(self.item, "error"):
            if self.item.error:
                return self.get_icon("error")
        if hasattr(self.item, "syncing"):
            if self.item.syncing:
                return self.get_icon("syncing")
        if hasattr(self.item, "syncd"):
            if self.item.syncd:
                return self.get_icon("success")
        return self.get_icon("load")

    def asset_status(self):
        if self.current_data == "Error":
            return self.get_icon("error")
        if not self.item.childItems:
            return self.get_icon("success")
        return self.get_icon("validate")
