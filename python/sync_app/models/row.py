import sgtk
from sgtk.platform.qt import QtCore, QtGui
from ..schema.schema import Schemas
from ..utils.inspection import method_decorator, trace
import uuid

# from ..lookups.sync_resolver import SyncResolver


logger = sgtk.platform.get_logger(__name__)

# schemas = Schemas()
transformer = None
# resolver = SyncResolver()


# @method_decorator(trace)
class Row:
    id = None

    def __init__(self, data, schema=None, resolver=None, primary=None, parent=None):
        self.id = str(uuid.uuid4())
        self.childItems = []
        self.data_in = data
        self.parentItem = parent

        self.resolver = resolver
        self.schema = schema

        self.should_be_visible = True

        if parent:
            parent.appendChild(self)

        self._cached_data = []
        # self._col_map = [i.get("key") for i in schema.schema]
        self.primary = primary

        # how we will render our data to the model
        self._serial_data = []

        # self.transformers = transformers
        # self.transformers = Transformers()

        self.column_schema = self.schema.schema
        # self.schema.schema = self.schemas[schema]
        # else:
        #     raise Exception("Schema-driven items require a schema to reference.")

        if not data:
            data = {"name": "None"}

    @property
    def rowData(self):
        if getattr(self, "resolver"):
            return self.resolver.resolve(self)

        return []

    @property
    def children(self):
        return self.childItems

    def visible_children(self):
        return len([i for i in self.childItems if i.should_be_visible])

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.rowData)

    def column(self):
        return self.columnCount()

    def isValid(self):
        return True

    def data(self, column, cached=False):
        try:
            # if cached:
            #     return self._cached_data
            # else:
            #     data = self.rowData[column]
            #     self._cached_data = data
            #     return data
            return self.rowData[column]
        except IndexError:
            return None

        # this runs in the model

    def parent(self):
        return self.parentItem

    def row(self):
        if hasattr(self, "primary"):
            if not self.primary:
                if self.parentItem:
                    return self.parentItem.childItems.index(self) + 1

        return 0

    ## Schema refactor into row as component of row VVVVV

    def header_data(self, index):
        return self.schema.schema[index].get("title")

    def set_data(self, index, value):
        self.data_in[self._col_map[index]] = value

    @property
    def _col_map(self):
        return [i.get("key") for i in self.schema.schema]
