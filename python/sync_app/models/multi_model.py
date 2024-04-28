import copy
import sgtk
from sgtk.platform.qt import QtCore, QtGui
from ..schema.schema import Schemas
from ..utils.inspection import method_decorator, trace
from ..lookups.sync_resolver import SyncResolver
from ..lookups.icon import IconManager
from .row import Row

logger = sgtk.platform.get_logger(__name__)


# @method_decorator(trace)
class MultiModel(QtCore.QAbstractItemModel):
    def __init__(self, data=None, parent=None):
        super(MultiModel, self).__init__(parent=parent)

        self.main_ui = parent
        self.primary_roots = {}
        self.paths = {}
        self.schemas = Schemas()
        self.resolver = SyncResolver()

        self.icon_manager = IconManager(icon_finder=self.main_ui.icon_path)
        self.rootItem = Row(
            data={}, parent=None, schema=self.schemas.asset_item, resolver=self.resolver
        )
        # self.rootItem will specify your headlines
        # TODO: pass your tree item in
        # self.rootItem = RowSchema(schema="sync_item_schema")

        # TODO: make this work with lists of lists of strings
        if data:
            self.setupModelData(data, self.rootItem)

        logger.debug("was able to set up the Model!! {}".format(data))

        # self.schemas =

    def columnCount(self, parent=None):
        if not parent:
            parent = self.rootItem
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    # def setData(self, index, value, role=None):
    #     item = index.internalPointer()
    #     item.set_data(index.column(), value)

    def data(self, index, role):

        if not index.isValid():
            return None

        col = index.column()

        if role not in [
            QtCore.Qt.DisplayRole,
            QtCore.Qt.UserRole,
            QtCore.Qt.DecorationRole,
            QtCore.Qt.SizeHintRole,
            QtCore.Qt.ToolTipRole,
        ]:
            return None
        item = index.internalPointer()
        if role == QtCore.Qt.DecorationRole:

            # Todo: uncomment this
            icon_static = item.column_schema[col].get("icon")
            #icon_static = None
            # logger.info()
            if icon_static:
                return self.icon_manager.get_icon(icon_static)

            # Todo: uncomment this
            icon_finder = item.column_schema[col].get("icon_finder")
            #icon_finder = None
            if icon_finder:
                if hasattr(self.icon_manager, icon_finder):
                    self.icon_manager.item = item
                    self.icon_manager.col = col
                    return getattr(self.icon_manager, icon_finder)()

        if role == QtCore.Qt.ToolTipRole:
            if hasattr(item, "tool_tip"):
                return item.tool_tip

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(30, 30)

        if role == QtCore.Qt.UserRole:
            # used to do simple child relation as UserData in the cell itself
            return item.row()

        else:
            return item.data(col)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return (
            QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemIsSelectable
            # | QtCore.Qt.ItemIsEditable
        )

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if hasattr(self.rootItem, "header_data"):
                return self.rootItem.header_data(section)
            return self.rootItem.data(section)

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=None):
        # if not parent:
        #     parent = self.rootItem
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def refresh(self):
        self.layoutAboutToBeChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()

    def add_row(self, data_item):
        if data_item.get("asset_name"):
            if not self.primary_roots.get(data_item["asset_name"]):
                asset_item = Row(
                    data=data_item,
                    parent=self.rootItem,
                    schema=self.schemas.asset_item,
                    resolver=self.resolver,
                    primary=True,
                )
                self.primary_roots[data_item["asset_name"]] = asset_item
            if data_item.get("item_found"):
                sync_item = Row(
                    data=data_item,
                    parent=self.primary_roots[data_item["asset_name"]],
                    schema=self.schemas.sync_item,
                    resolver=self.resolver,
                )

            self.refresh()

        # lines is our list

    def item(self, index):
        if not index.isValid():
            return self.rootItem
        else:
            return index.internalPointer()

    def setupModelData(self, data, parent):

        for list_item in data:
            self.add_row(list_item)
