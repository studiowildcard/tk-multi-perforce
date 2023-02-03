from sgtk.platform.qt import QtCore, QtGui


class ProgressDelegate(QtGui.QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = 50
        opt = QtGui.QStyleOptionProgressBar()
        # opt.setMaxiumumHeight(10)
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = progress
        opt.text = "{}%".format(progress)
        opt.textVisible = True
        QtGui.QApplication.style().drawControl(
            QtGui.QStyle.CE_ProgressBar, opt, painter
        )


class MultiDelegate(QtGui.QStyledItemDelegate):
    """
    A delegate class displaying a double spin box.
    https://stackoverflow.com/questions/61663446/with-pyside2-and-qtableview-how-do-i-get-multiple-delegates-in-table-view-using
    """

    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        pass

    def createEditor(self, parent, option, index):
        editor = QtGui.QProgressBar(parent)
        return editor

    def setEditorData(self, spinBox, index):
        pass

    def setModelData(self, spinBox, model, index):
        return True

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class DoubleSpinBoxDelegate(QtGui.QStyledItemDelegate):
    """
    A delegate class displaying a double spin box.
    https://stackoverflow.com/questions/61663446/with-pyside2-and-qtableview-how-do-i-get-multiple-delegates-in-table-view-using
    """

    def __init__(self, parent=None, minimum=0.0, maximum=100.0, step=0.01):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self._min = minimum
        self._max = maximum
        self._step = step

    def createEditor(self, parent, option, index):
        row_index = index.data(QtCore.Qt.UserRole)
        if row_index == 1:
            editor = QtGui.QDoubleSpinBox(parent)
            editor.setMinimum(self._min)
            editor.setMaximum(self._max)
            editor.setSingleStep(self._step)
            editor.setAccelerated(True)
            editor.installEventFilter(self)
            return editor

    def setEditorData(self, spinBox, index):
        value = float(index.model().data(index, QtCore.Qt.DisplayRole))
        spinBox.setValue(value)

    def setModelData(self, spinBox, model, index):
        value = spinBox.value()
        model.setData(index, value)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
