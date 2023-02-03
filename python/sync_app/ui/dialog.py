import logging
import os
import sys
from functools import partial

import sgtk
from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt import QtCore, QtGui

from ..utils.local_workspace import open_browser
from .base_ui import Ui_Generic
from ..models.multi_model import MultiModel
from ..models.model_filter import SortFilterModel
from ..utils.inspection import method_decorator, trace
from .delegates import ProgressDelegate

logger = sgtk.platform.get_logger(__name__)
COLORS = {
    "red": (165, 66, 61),
    "orange": (194, 115, 59),
    "yellow": (226, 184, 67),
    "olive": (192, 201, 81),
    "green": (87, 178, 98),
    "teal": (75, 206, 192),
    "blue": (78, 131, 168),
    "violet": (99, 72, 143),
    "purple": (136, 75, 147),
    "pink": (161, 65, 112),
}


class Badge(QtGui.QLabel):
    def __init__(
        self,
        text=None,
        color="red",
        opacity=50,
        padding=1,
        font_size=10,
        *args,
        **kwargs,
    ):
        super(Badge, self).__init__(*args, **kwargs)
        self.font_size = font_size
        self.setText(text.upper())
        self.set_color(color, opacity=opacity)

    def set_color(self, color=None, opacity=50):
        self.setStyleSheet(
            f"""QLabel {{
                           background-color:rgba({COLORS[color][0]},{COLORS[color][1]},{COLORS[color][2]},{opacity});
                           color:{255, 255, 255};
                           border-radius:5px;
                           font-size:{self.font_size}px;
                           padding-left:{self.font_size * 0.35}px;
                           padding-right:{self.font_size * 0.35}px;
                           padding-top:{self.font_size * 0.35}px;
                           padding-bottom:{self.font_size * 0.35}px;
                           }}
                           QToolTip {{opacity: 180;
                                font-size:11px;
                                padding: 5px;
                                border-radius: 5px;
                                background-color: rgb(40, 40, 40);
                                color: rgb(250,250,250);
                           }}"""
        )


class SelectionItem(QtGui.QListWidgetItem):
    def __init__(self, name, parent=None, logger=None):
        """
        Construction of generic base ui, containing
        common utilities and methods for Ui state and management

        Super-ing this class at the end of your inherited class allows you to specify the
        widgets and layout as you wish first, and this base class will build it for you
        """
        super(SelectionItem, self).__init__(parent)

        self._widget = QtGui.QWidget()
        self.main_layout = QtGui.QVBoxLayout()
        self.info_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.info_layout)
        self._widget.setLayout(self.main_layout)

        self._counter = 0

        title_label = QtGui.QLabel(name)
        title_label.setStyleSheet(f"font-size: 16px;")

        self.badge_count = Badge("0")
        self.badge_status = Badge("syncing...", font_size=10, color="green")
        self.info_layout.addWidget(title_label)
        self.info_layout.addWidget(self.badge_count)
        self.info_layout.addWidget(self.badge_status)
        self.info_layout.addStretch(1)

        self.progress = QtGui.QProgressBar()
        self.progress.setMaximumHeight(5)
        self.progress.setRange(0, 100)
        self.progress.setFormat("")
        self.progress.setVisible(False)

        self.main_layout.addWidget(self.progress)

        self.set_status("init")
        # self.set_counter(0)

        self.setSizeHint(self._widget.sizeHint())

    def set_progress(self, value):
        if 100 > value > 0:
            self.progress.setValue(value)
            self.progress.setVisible(True)
        else:
            self.progress.setVisible(False)

    def set_status(self, status):
        meta = {"In Sync": "green", "Syncing...": "blue"}
        if status in meta:
            self.badge_status.setVisible(True)
            self.badge_status.set_color(meta[status])
            self.badge_status.setText(status)
        else:
            self.badge_status.setVisible(False)

    def set_counter(self, count):
        self._counter = count

        if self._counter > 0:
            self.badge_count.setText(str(count))
            self.badge_count.setVisible(True)
        else:
            self.badge_count.setVisible(False)
            self.set_status("In Sync")


class ItemSelector(QtGui.QWidget):
    item_selected = QtCore.Signal(dict)

    def __init__(self, parent, logger=None):
        """
        Construction of generic base ui, containing
        common utilities and methods for Ui state and management

        Super-ing this class at the end of your inherited class allows you to specify the
        widgets and layout as you wish first, and this base class will build it for you
        """
        super(ItemSelector, self).__init__(parent)
        self.logger = logger
        self._items = {}
        self._widgets = {}
        self._index = []
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.list_widget = QtGui.QListWidget()
        self.main_layout.addWidget(self.list_widget)

        self.list_widget.currentRowChanged.connect(self.item_clicked)

    def update_item_summary(self, data):
        model_name = data.get("name")
        left_to_sync = data.get("items") - data.get("in_sync")
        if data.get("items"):
            progress = (float(data.get("in_sync")) / float(data.get("items"))) * 100
        self._widgets[model_name].set_counter(left_to_sync)
        self._widgets[model_name].set_progress(int(progress))

    def set_color(self, *colors):

        r = sum([COLORS[c][0] for c in colors]) / len(colors)
        g = sum([COLORS[c][1] for c in colors]) / len(colors)
        b = sum([COLORS[c][2] for c in colors]) / len(colors)
        self.color_bar.setStyleSheet(
            "background-color:rgb(%d, %d, %d);border-radius:3px" % (r, g, b)
        )

    def add_item(self, key, data):
        try:
            if key not in self._items:
                self._items[key] = data
                self._index.append(key)

                item = SelectionItem(key)
                self._widgets[key] = item
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, item._widget)

        except Exception as e:
            import traceback

            self.logger.error(traceback.format_exc())

    def item_clicked(self, index):
        name = self._index[index]
        self.item_selected.emit(self._items[name])


class ItemDetailsPane(QtGui.QWidget):
    def __init__(self, name, parent=None, logger=None):
        """
        Construction of generic base ui, containing
        common utilities and methods for Ui state and management

        Super-ing this class at the end of your inherited class allows you to specify the
        widgets and layout as you wish first, and this base class will build it for you
        """
        super(ItemDetailsPane, self).__init__(parent)
        self.parent = parent
        self.setContentsMargins(0, 0, 0, 0)
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.text = QtGui.QLabel(name)

        # layout.addWidget(button)

        self.model = MultiModel(parent=self.parent.parent)
        self.proxy_model = SortFilterModel(excludes=[None], parent=self.parent.parent)

        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)

        self.tree_view = QtGui.QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.main_layout.addWidget(self.text)
        self.main_layout.addWidget(self.tree_view)


class ItemDetailsWidget(QtGui.QWidget):
    model_summary = QtCore.Signal(dict)

    def __init__(self, parent, logger=None):
        """
        Construction of generic base ui, containing
        common utilities and methods for Ui state and management

        Super-ing this class at the end of your inherited class allows you to specify the
        widgets and layout as you wish first, and this base class will build it for you
        """
        super(ItemDetailsWidget, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.parent = parent
        self.logger = logger

        self._current_item = None

        self._views = {}
        self._models = {}
        self._proxy_models = {}
        self._items = {}
        self._buttons = {}

        self._details = {}

        self.stack = QtGui.QStackedWidget()

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addWidget(self.stack)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

    def add_details_pane(self, name, data):
        # adds details pane for

        # make the view
        widget = QtGui.QWidget()
        self._details[name] = ItemDetailsPane(name, parent=self)

        self.stack.addWidget(self._details[name])

        # self.show_details_pane(name)

    def show_details_pane(self, name):

        if self._details.get(name):
            self._current_item = name
            self.refresh()
            self.stack.setCurrentWidget(self._details[name])

    def summarize_model(self, key):
        doc = {
            "items": self._details[key].model.rootItem.visible_children(),
            "name": key,
            "in_sync": self._details[key].model.rootItem.syncd_children(),
        }
        self.model_summary.emit(doc)

    def refresh(self):
        if self._current_item:
            if self._details.get(self._current_item):
                self.summarize_model(self._current_item)
                self._details[self._current_item].model.refresh()

    def add_item_details(self, name, data):
        if not name in self._details:
            self._current_item = name
            self.add_details_pane(name, data)
        self._details[name].model.add_details(data)

        self._details[name].model.refresh()
        self.summarize_model(name)


@method_decorator(trace)
class Ui_Dialog(Ui_Generic):
    """
    Description:
        A class for the construction of sync app UI.
    """

    def __init__(self, parent, app, **kwargs):

        """
        Description:
            Construction of sync UI. Note that order of init matters
        """

        self.progress_handler = None  # Init a progress handler
        self.app = app
        super(Ui_Dialog, self).__init__(parent, **kwargs)
        self.app.ui = self  # set public property to UI
        self.app.setup()  # since we use SG to handle our UI display, we defer the app init until the UI is ready.

    def make_components(self):

        # the utility that routes the data into a table/view
        self.model = MultiModel(parent=self, header_schema="asset_title")
        self.proxy_model = SortFilterModel(excludes=[None], parent=self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)

        # assert filterable keys from the chosen schema
        self.list_of_filter_types = self.model.schemas.sync_item.extract_filters()

    def make_widgets(self):
        """
        Makes UI widgets for the main form
        """

        self.log_window = (
            listWidget()
        )  # Create the perforce raw data log widget. Note that we are using our custon QlistWidget Class
        self.log_window.setSortingEnabled(True)  # enables sorting on the list widget
        self.log_window.setSelectionMode(
            QtGui.QAbstractItemView.MultiSelection
        )  # enable multi selection on the list widget

        self._do = QtGui.QPushButton("Sync")  # create sync button

        self._asset_tree = QtGui.QTreeWidget()  # create asset tree
        self._asset_tree.clear()

        self._items_tree = QtGui.QTreeWidget()

        self._progress_bar = QtGui.QProgressBar()  # create progress bar
        self._global_progress_bar = QtGui.QProgressBar()  # create progress bar
        self._list = QtGui.QListWidget()
        self._reset_filters = QtGui.QPushButton()  # create reset filter toggle
        self._hide_syncd = QtGui.QCheckBox()  # create hide if nothing to sync toggle
        self._force_sync = QtGui.QCheckBox()  # create the force sync toggle
        self._force_sync.setText("Force Sync")
        self._rescan = QtGui.QPushButton("Rescan")
        self.tree_view = QtGui.QTableView()

        self.tree_view.setItemDelegateForColumn(1, ProgressDelegate(self.tree_view))

        self._perforce_log_viewstate = QtGui.QCheckBox()
        self._perforce_log_viewstate.setText("Show perforce log")

        self.view_stack = QtGui.QStackedWidget()
        self.b = QtGui.QLabel(
            "<center><h3>Gathering contextual request from Perforce Servers for:<br></h3><h5> {} items...</center>".format(
                str(len(self.app.input_data))
            )
        )

    def reload_view(self):

        self.model.i_should_update = True
        self.model.refresh()
        self.tree_view.update()
        # self.tree_view.expandAll()
        # self.tree_view.setAnimated(True)
        self.show_tree()
        # record time of update into self.last_updated

    def setup_style(self):
        self.setStyleSheet(
            """
            QTreeView::item { padding: 5px; }
            QAction  { padding: 10px; }
        """
        )

    def setup_ui(self):
        """
        Lays out and customizes widgets for the main form
        """
        # set main layout
        self._main_layout = QtGui.QVBoxLayout()
        self._menu_layout = QtGui.QHBoxLayout()

        self.items_widget = QtGui.QWidget()
        self.items_splitter = QtGui.QSplitter()

        self.items_list = ItemSelector(self, self.logger)
        self.items_list.item_selected.connect(self.item_context_changed)
        self.items_splitter.addWidget(self.items_list)
        self.t2 = QtGui.QTreeView()
        self.t3 = QtGui.QTreeView()

        self.item_details_widget = ItemDetailsWidget(self)
        # connect our model to our list widghet to feed it info
        self.item_details_widget.model_summary.connect(
            self.items_list.update_item_summary
        )
        self.items_splitter.addWidget(self.item_details_widget)

        self.items_splitter.setStretchFactor(1, 4)

        # self.items_widget.setLayout(self.items_layout)

        self.setLayout(self._main_layout)

        self._progress_bar.setVisible(False)  # hide progress until we run the sync
        self.log_window.setVisible(False)  # hide until requested to show

        self.tree_view.setModel(self.proxy_model)
        # self.tree_view.setAnimated(True)

        self.view_stack.addWidget(self.items_splitter)
        self.view_stack.addWidget(self.b)
        self.view_stack.setCurrentWidget(self.b)

        # set main tree style
        self._asset_tree.setAnimated(True)
        self._asset_tree.setWordWrap(True)

        self._hide_syncd.setText("Hide if nothing to sync")
        self._reset_filters.setText("Reset Filters")

        self._global_progress_bar.setMaximumHeight(10)

        self._menu_layout.addWidget(
            self._hide_syncd
        )  # add hide if nothing to sync toggle
        self._menu_layout.addStretch()

        self.sync_layout = QtGui.QHBoxLayout()
        self.sync_layout.addWidget(self._rescan, 3)
        self.sync_layout.addWidget(self._do, 10)
        self.sync_layout.addWidget(self._force_sync, 1)

        # perforce log layout
        self.perforce_log_layout = QtGui.QVBoxLayout()
        self.perforce_log_layout.addWidget(self._perforce_log_viewstate)
        self.perforce_log_layout.addWidget(self.log_window)

        # arrange widgets in layout
        self._main_layout.addLayout(self._menu_layout)
        self._main_layout.addWidget(self.view_stack)
        self._main_layout.addWidget(self._progress_bar)
        self._main_layout.addLayout(self.sync_layout)
        self._main_layout.addLayout(self.perforce_log_layout)
        self._menu_layout.addWidget(self._reset_filters)

        # TODO connect reset filter button
        self._reset_filters.clicked.connect(self.reset_all_filters)

        # connect the hide if nothing to sync button
        self._hide_syncd.clicked.connect(self.filtered)

        # connect the perforce viewstate toggle
        self._perforce_log_viewstate.clicked.connect(self.toggle_perforce_log)

        for widget in [self._do, self._force_sync, self._rescan]:  # , self.tree_view]:
            self.centrally_control_enabled_state(widget)

        for filter_type in self.list_of_filter_types:
            self.button_menu_factory(filter_type)

        self._rescan.clicked.connect(self.rescan)

        self.resize(900, 800)

        self.setup_views()

        # connect right_click_menu to tree
        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.open_context_menu)
        self.tree_view.selectionModel().selectionChanged.connect(
            self.item_context_changed
        )

        # emulate UI event of triggering filters
        self.filter_triggered()

        # self.interactive = False
        self.show_waiting()

    def rescan(self):

        self.model = MultiModel(parent=self, header_schema="asset_title")
        self.proxy_model.setSourceModel(self.model)
        self.log_window.clear()
        self.model.refresh()
        self.app.initialize_data()

    def setup_events(self):
        pass
        # self._do.clicked.connect(self.start_sync)

    def toggle_perforce_log(self):

        """
        Description:
            Hides/unhides the perforce log in the sync app UI
        """

        if not self.log_window.isVisible():
            self.log_window.setVisible(True)

        else:
            self.log_window.setVisible(False)

    def update_progress(self):
        if self.progress_handler:

            if len(self.progress_handler.queue.keys()) > 1:
                self._global_progress_bar.setVisible(True)

            self._global_progress_bar.setRange(0, 100)
            self._progress_bar.setVisible(True)
            self._progress_bar.setRange(0, 100)

            if not self.progress_handler.progress == 1:
                self._progress_bar.setValue(self.progress_handler.progress * 100)

            else:
                self._progress_bar.setVisible(False)
                self._progress_bar.setValue(0)
                self._global_progress_bar.setVisible(False)
                self._global_progress_bar.setValue(0)

    def icon_path(self, name):
        # icon_path = None
        icon_path = self.app.shotgun_globals.icon.get_entity_type_icon_url(name)

        if not icon_path:
            icon_path = os.path.join(
                self.app.basepath, "ui", "icons", "status_{}.png".format(name)
            )
        return icon_path

    def make_icon(self, name):
        """
        Convenience maker of icons if following a given naming pattern.

        Args:
            name (str): name of the icon on disk, to be inserted into `status_{}.png`

        Returns:
            QtGui.QIcon: Path'd QIcon ready to set to a button or widget's setIcon() func
        """

        return QtGui.QIcon(self.icon_path(name))

    def open_context_menu(self, point):

        try:

            os_filebrowser_map = {"win32": "Explorer", "darwin": "Finder"}
            # get proper browser based on OS
            os_filebrowser = "file browser"
            if sys.platform in os_filebrowser_map.keys():
                os_filebrowser = os_filebrowser_map[sys.platform]

            # find the index of the SortFilterProxy item we selected
            filtered_item_model_index = self.tree_view.indexAt(
                point
            )  # This is the index that needs to be mapped

            # map from the SortFilterProxy item to the original model pointer, get Row item from it
            pointer_to_source_item = self.proxy_model.mapToSource(
                filtered_item_model_index
            ).internalPointer()

            # find index of chosen key to look up when right clicking
            column_index = pointer_to_source_item.schema.key_index_map.get(
                "item_found"
            )  # get index of the column

            path_to_open = os.path.dirname(
                pointer_to_source_item.rowData[column_index]
            )  # retrieve the path for that item on on the given index

            menu = QtGui.QMenu()
            action = menu.addAction(
                "Open path in {}".format(os_filebrowser),
                partial(open_browser, path_to_open),
            )

            menu.exec_(self.tree_view.mapToGlobal(point))

            logger.debug(
                "Opened file browser via context menu for path: {}".format(path_to_open)
            )

        except Exception as e:

            logger.error("Error occurred starting context menu: {}".format(e))

    def show_if_filter_is_enabled(self, filter_type="ext"):

        filter_dropdown = getattr(self, "_{}_filter".format(filter_type))
        filter_actions = getattr(self, "_{}_actions".format(filter_type))

        if not all([i.isChecked() for i in filter_actions.values()]):
            filter_dropdown.setIcon(self.make_icon("filter"))
        else:
            filter_dropdown.setIcon(QtGui.QIcon())

    def update_available_filters(self, filter_info):

        """
        Description:
            Runs when the sync worker returns with a filter type and the extension

        filter_info:
            [Tuple] ("step", "Rigging")


        TODO: implement during scraping/transformation of data
        Populate the steps filter menu as steps are discovered in the p4 scan search
        """

        filter_type = filter_info[0]  # looks like this is always returning 'ext'

        filter_value = filter_info[1]  # file extensions like: tga, jpeg, ma, max etc

        actions = getattr(self, "_{}_actions".format(filter_type))

        filter_dropdown = getattr(self, "_{}_filter".format(filter_type))

        filter_dropdown.setIcon(QtGui.QIcon())

        if filter_value not in actions.keys():
            action = QtGui.QAction(self)

            action.setCheckable(True)

            self.utils.prefs.read()
            filters = self.utils.prefs.data.get(
                "{}_filters".format(filter_type)
            )  # dictionary containing filter settings for user.

            check_state = True

            if filters:

                if filter_value in filters.keys():
                    # tga : True, jpeg: False, png: True
                    check_state = filters[
                        filter_value
                    ]  # retrieve filter state from preference. True or False

            action.setChecked(check_state)
            action.setText(str(filter_value))

            action.triggered.connect(self.filter_triggered)

            getattr(self, "_{}_menu".format(filter_type)).addAction(action)
            actions[filter_value] = action

        self.show_if_filter_is_enabled(filter_type)

    def setup_views(self):

        if getattr(self.model.rootItem, "column_schema"):
            schema = self.model.rootItem.column_schema

            for view in [self.tree_view]:
                self.logger.info("setting up view: {}".format(schema))

                for c, col_def in enumerate(schema):

                    if col_def.get("width"):
                        view.setColumnWidth(c, col_def["width"])

    def reset_all_filters(self):

        for filter_type in self.list_of_filter_types:
            if hasattr(self, "_{}_actions".format(filter_type)):
                actions = getattr(self, "_{}_actions".format(filter_type))
                if actions:
                    for checkbox in actions.values():

                        checkbox.setChecked(True)
        self.filter_triggered()

    def filter_triggered(self):
        """
        Description:
            description here
        """

        preference_data = self.utils.prefs.read()

        for filter_type in self.list_of_filter_types:

            filter_type = filter_type.lower()
            preference_filter_name = "{}_filters".format(filter_type)
            filter_data = {}

            # use existing filter data if exists
            if preference_data.get(preference_filter_name):
                filter_data = preference_data.get(preference_filter_name)

            # overwrite it with  our scan of presently checked items
            if hasattr(self, "_{}_actions".format(filter_type)):
                actions = getattr(self, "_{}_actions".format(filter_type))
                if actions:
                    for k, v in actions.items():
                        filter_data[k] = v.isChecked()

            preference_data[preference_filter_name] = filter_data

            # update user preference data on disk
            self.utils.prefs.write(preference_data)

            # show the filter enabled icon in the ui
            self.show_if_filter_is_enabled(filter_type)

        self.filtered()

    def button_menu_factory(self, name: str = None):

        """
        Description:
            A factory method to creating buttons used for the filtering menu

        name -> str:
            name of the button
        """

        width = 80  # fixed with used in UI on the filter menu entry
        short_name = name.lower().replace(
            " ", ""
        )  # format name to single lowercase string with no spaces

        setattr(
            self, "_{}_filter".format(short_name), QtGui.QToolButton()
        )  # store description of QToolbutton as attribute: object, name, value.
        setattr(
            self, "_{}_menu".format(short_name), QtGui.QMenu()
        )  # store description of QMenu as attribute: object, name, value.
        setattr(self, "_{}_actions".format(short_name), {})

        btn = getattr(self, "_{}_filter".format(short_name))  #
        menu = getattr(self, "_{}_menu".format(short_name))  #

        btn.setFixedWidth(width)  # set fixed width on button
        btn.setText(name)  # set text on button
        btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )  # set text next to boolean operator
        btn.setMenu(menu)  # associate button with menu
        btn.setPopupMode(
            QtGui.QToolButton.InstantPopup
        )  # when clicked the "dropdown" opens instantly

        menu.setFixedWidth(width)  # set menu button to fixed width
        menu.setTearOffEnabled(True)  # enable the ability to tear off the menu item

        self.logger.error(str(getattr(self, "_{}_actions".format(short_name))))

        self._menu_layout.addWidget(btn)  # add btn to menu widget

    def filtered(self):
        """
        Desription:
            This method runs when the any of the filters is changed, and ensures that the ui is updated accordingly.
        """
        logging.debug("Refreshing UI based on changes")
        # if self.interactive:
        self.model.refresh()

        self.item_details_widget.refresh()

    def show_tree(self):
        self.view_stack.setCurrentWidget(self.items_splitter)

    def show_waiting(self):
        self.view_stack.setCurrentWidget(self.b)

    def item_context_changed(self, test=None):
        """
        Resolves the model item row when clicked.


        """
        # index = self.tree_view.selectedIndexes()[0]
        # # crawler = index.model().itemFromIndex(index)

        # pointer_to_source_item = self.proxy_model.mapToSource(index).internalPointer()

        # name = pointer_to_source_item.data(0)
        self.logger.info(str(test))
        self.item_details_widget.show_details_pane(test.get("asset_name"))


class listWidget(QtGui.QListWidget):
    """
    Description:
        This class is an a small extension of QlistWidget which will allow the widget to detect when CTRL + C is pressed
        and store the information on the clipboard. The issue with a QlistWidget is that even with .multiSelect(Enabled) the copy paste function only allows us to copy one row.
        We can get around this by creating one continous string that we just format with a line break \ n
    """

    def keyPressEvent(self, event):
        """
        Description:


            The keyPressEvent is a build in method for the QWidget and allows us to monitor any keys pressed.
            This event handler, can be reimplemented in a subclass to receive key press events for the widget.
            In this case we are looking for the copy combination CTRL + C

        event:
            the keys getting pressed
        """

        if event.matches(
            QtGui.QKeySequence.Copy
        ):  # if the pressed keys matches the copy combination

            values = []  # init empty list to store what needs to be copied

            for item in self.selectedIndexes():  # for each item selected

                values.append(item.data())  # add it into the values list

            QtGui.QApplication.clipboard().setText(
                "\n".join(values)
            )  # create one long string out of all the list entries, but format them with a seperate line

        return
