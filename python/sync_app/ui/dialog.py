import logging
import os
import sys
import urllib
import tempfile
import shutil

from functools import partial

import sgtk

from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt import QtCore, QtGui
from tank.platform.qt5 import QtWidgets

from ..workers.sync_worker import SyncWorker, AssetInfoGatherWorker
from ..utils.local_workspace import open_browser
from .base_ui import Ui_Generic
from ..models.multi_model import MultiModel
from ..models.model_filter import SortFilterModel

from ..details.model_status import SgStatusModel
from ..details.model_latestpublish import SgLatestPublishModel

from ..details.model_publishhistory import SgPublishHistoryModel

from ..details.delegate_publish_history import SgPublishHistoryDelegate

from ..details.loader_action_manager import LoaderActionManager

logger = sgtk.platform.get_logger(__name__)

# import frameworks
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)
settings = sgtk.platform.import_framework("tk-framework-shotgunutils", "settings")
help_screen = sgtk.platform.import_framework("tk-framework-qtwidgets", "help_screen")
overlay_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget"
)
shotgun_search_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_search_widget"
)
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)

ShotgunModelOverlayWidget = overlay_widget.ShotgunModelOverlayWidget


# @method_decorator(trace)
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

        self._action_manager = LoaderActionManager()
        self._sg = None

        self._sg_data = {}
        self._row_data = {}

        self._key = None
        self._id = 0
        self.dir_path = tempfile.mkdtemp()
        #
        # create a background task manager
        self._task_manager = task_manager.BackgroundTaskManager(
            self, start_processing=True, max_threads=2
        )
        shotgun_globals.register_bg_task_manager(self._task_manager)

        # hook a helper model tracking status codes so we
        # can use those in the UI
        self._status_model = SgStatusModel(self, self._task_manager)
        self.init_details_panel()

    def get_row_data(self, app, row_data):
        """
        Merge row_data into self._row_data
        """
        # set the shotgun instance
        self._sg = app.shotgun
        for key in row_data.keys():
            if key not in self._row_data.keys():
                self._row_data[key] = row_data[key]

    def get_sg_data(self, app, dict_data):
        """
        Merge dict_data into self._sg_data
        """
        self._sg = app.shotgun
        for key in dict_data.keys():
            if key not in self._sg_data.keys():
                self._sg_data[key] = dict_data[key]


    def make_components(self):

        # the utility that routes the data into a table/view
        self.model = MultiModel(parent=self)
        self.proxy_model = SortFilterModel(excludes=[None], parent=self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)

        # assert filterable keys from the chosen schema
        self.list_of_filter_types = self.model.schemas.sync_item.extract_filters()

    def make_widgets(self):
        """
        Makes UI widgets for the main form
        """
        """
        self.log_window = (
            listWidget()
        )  # Create the perforce raw data log widget. Note that we are using our custon QlistWidget Class
        self.log_window.setSortingEnabled(True)  # enables sorting on the list widget
        self.log_window.setSelectionMode(
            QtGui.QAbstractItemView.MultiSelection
        )  # enable multi selection on the list widget
        # self.log_window.setMinimumHeight(200)
        # self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        """

        self.log_window = QtWidgets.QTextBrowser()
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        self.log_window.setMinimumHeight(200)

        self._do = QtGui.QPushButton("Sync")  # create sync button

        self._asset_tree = QtGui.QTreeWidget()  # create asset tree
        self._asset_tree.clear()

        self._progress_bar = QtGui.QProgressBar()  # create progress bar
        self._global_progress_bar = QtGui.QProgressBar()  # create progress bar
        self._list = QtGui.QListWidget()
        self._reset_filters = QtGui.QPushButton()  # create reset filter toggle
        self._hide_syncd = QtGui.QCheckBox()  # create hide if nothing to sync toggle
        self._force_sync = QtGui.QCheckBox()  # create the force sync toggle
        self._force_sync.setText("Force Sync")
        self._rescan = QtGui.QPushButton("Rescan")
        self.tree_view = QtGui.QTreeView()

        self._perforce_log_viewstate = QtGui.QCheckBox()
        self._perforce_log_viewstate.setText("Show perforce log")
        # self._perforce_log_viewstate.setChecked(False)
        self._perforce_log_viewstate.setChecked(True)

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
        self.tree_view.expandAll()
        self.tree_view.setAnimated(True)
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
        self._gui_layout = QtGui.QHBoxLayout()
        self._main_layout = QtGui.QVBoxLayout()
        self._menu_layout = QtGui.QHBoxLayout()

        #self.setLayout(self._main_layout)
        self.setLayout(self._gui_layout)

        self._progress_bar.setVisible(False)  # hide progress until we run the sync
        # self.log_window.setVisible(False)  # hide until requested to show
        self.log_window.setVisible(True)

        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setAnimated(True)

        self.view_stack.addWidget(self.tree_view)
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
        self.perforce_log_layout.setContentsMargins(0, 5, 0, 5)
        self.perforce_log_layout.addWidget(self._perforce_log_viewstate)
        self.perforce_log_layout.addWidget(self.log_window)

        # Add info button
        self.info = QtGui.QToolButton()
        self.info.setMinimumSize(QtCore.QSize(80, 26))
        self.info.setObjectName("info")
        self.info.setToolTip("Use this button to <i>toggle details on and off</i>.")
        self.info.setText("Show Details")
        #self.info.setText("Hide Details")

        # arrange widgets in layout
        self._main_layout.addLayout(self._menu_layout)
        self._main_layout.addWidget(self.view_stack)
        self._main_layout.addWidget(self._progress_bar)
        self._main_layout.addLayout(self.sync_layout)
        self._main_layout.addLayout(self.perforce_log_layout)


        # details layout
        self._no_selection_pixmap = QtGui.QPixmap(":/res/no_item_selected_512x400.png")
        # self._no_pubs_found_icon = QtGui.QPixmap(":/res/no_publishes_found.png")
        # self._no_pubs_found_icon = QtGui.QPixmap(":/tk_multi_perforce/no_publishes_found.png")
        self._no_pubs_found_icon = QtGui.QPixmap(":/res/no_item_selected_512x400.png")

        self.details_layout = QtGui.QVBoxLayout()
        self.details_layout.setSpacing(2)
        self.details_layout.setContentsMargins(4, 4, 4, 4)
        self.details_layout.setObjectName("details_layout")

        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 5, 0, 25)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.details_image = QtGui.QLabel()
        """
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.details_image.sizePolicy().hasHeightForWidth())
        self.details_image.setSizePolicy(sizePolicy)
        
        
        """
        self.details_image.setMinimumSize(QtCore.QSize(256, 200))
        self.details_image.setMaximumSize(QtCore.QSize(256, 200))
        #self.details_image.setScaledContents(True)
        self.details_image.setAlignment(QtCore.Qt.AlignCenter)

        self.details_image.setObjectName("details_image")
        #self.details_image.setPixmap(self._no_selection_pixmap)
        self.details_image.setPixmap(self._no_selection_pixmap.scaled(
            self.details_image.width(), self.details_image.height(), QtCore.Qt.KeepAspectRatio))
        self.horizontalLayout.addWidget(self.details_image)
        spacerItem3 = QtGui.QSpacerItem(40, 40, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)
        self.details_layout.addLayout(self.horizontalLayout)

        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.details_header = QtGui.QLabel()
        self.details_header.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.details_header.setWordWrap(True)
        self.details_header.setObjectName("details_header")
        #self.details_header.setMinimumSize(QtCore.QSize(300, 150))
        #self.details_header.setMaximumSize(QtCore.QSize(300, 150))
        self.horizontalLayout_5.addWidget(self.details_header)
        spacerItem4 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem4)
        self.verticalLayout_4 = QtGui.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.detail_playback_btn = QtGui.QToolButton()
        self.detail_playback_btn.setMinimumSize(QtCore.QSize(55, 55))
        self.detail_playback_btn.setMaximumSize(QtCore.QSize(55, 55))
        self.detail_playback_btn.setText("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/res/play_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.detail_playback_btn.setIcon(icon4)
        self.detail_playback_btn.setIconSize(QtCore.QSize(40, 40))
        self.detail_playback_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.detail_playback_btn.setObjectName("detail_playback_btn")
        self.detail_playback_btn.setToolTip(
            "The most recent published version has some playable media associated. Click this button to launch the ShotGrid <b>Media Center</b> web player to see the review version and any notes and comments that have been submitted.")

        self.verticalLayout_4.addWidget(self.detail_playback_btn)
        self.detail_actions_btn = QtGui.QToolButton()
        self.detail_actions_btn.setMinimumSize(QtCore.QSize(55, 0))
        self.detail_actions_btn.setMaximumSize(QtCore.QSize(55, 16777215))
        self.detail_actions_btn.setPopupMode(QtGui.QToolButton.InstantPopup)
        self.detail_actions_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.detail_actions_btn.setObjectName("detail_actions_btn")
        self.detail_actions_btn.setText("Actions")
        self.verticalLayout_4.addWidget(self.detail_actions_btn)

        self.horizontalLayout_5.addLayout(self.verticalLayout_4)
        self.details_layout.addLayout(self.horizontalLayout_5)

        self.version_history_label = QtGui.QLabel()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.version_history_label.sizePolicy().hasHeightForWidth())
        self.version_history_label.setSizePolicy(sizePolicy)
        self.version_history_label.setStyleSheet("QLabel { padding-top: 14px}")
        self.version_history_label.setAlignment(QtCore.Qt.AlignCenter)
        self.version_history_label.setWordWrap(True)
        self.version_history_label.setObjectName("version_history_label")
        self.version_history_label.setText("<small>Complete Version History</small>")
        # self.version_history_label.setText(QtGui.QApplication.translate("Dialog", "<small>Complete Version History</small>", None, QtGui.QApplication.UnicodeUTF8))
        self.details_layout.addWidget(self.version_history_label)

        self.history_view = QtGui.QListView()
        self.history_view.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.history_view.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.history_view.setUniformItemSizes(True)
        self.history_view.setObjectName("history_view")
        self.details_layout.addWidget(self.history_view)

        self.container_widget = QtGui.QWidget()
        self.container_widget.setLayout(self.details_layout)
        self.container_widget.setFixedWidth(300)
        self.container_widget.setVisible(False)

        # arrange widgets in gui layout
        self._gui_layout.addLayout(self._main_layout)
        # self._gui_layout.addLayout(self.details_layout)
        self._gui_layout.addWidget(self.container_widget)

        # TODO connect reset filter button
        self._reset_filters.clicked.connect(self.reset_all_filters)

        # connect the hide if nothing to sync button
        self._hide_syncd.clicked.connect(self.filtered)

        # connect the perforce viewstate toggle
        self._perforce_log_viewstate.clicked.connect(self.toggle_perforce_log)

        # _menu_layout
        for widget in [self._do, self._force_sync, self._rescan]:  # , self.tree_view]:
            self.centrally_control_enabled_state(widget)

        self._menu_layout.addWidget(self._reset_filters)

        for filter_type in self.list_of_filter_types:
            self.button_menu_factory(filter_type)


        self._menu_layout.addWidget(self.info)

        self._rescan.clicked.connect(self.rescan)

        self.resize(1250, 800)

        self.setup_views()

        # Single click on tree item
        self.tree_view.clicked.connect(self.on_item_clicked)
        #self.tree_view.itemDoubleClicked.connect(self.on_item_clicked)

        # connect right_click_menu to tree
        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.open_context_menu)

        # emulate UI event of triggering filters
        self.filter_triggered()

        self.interactive = True
        self.show_waiting()
        self.reset_all_filters()

    def add_log(self, msg):
        self.log_window.append(msg)
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())


    def init_details_panel(self):

        # details pane
        # self._details_pane_visible = False
        self._details_pane_visible = True

        self._details_action_menu = QtGui.QMenu()
        self.detail_actions_btn.setMenu(self._details_action_menu)

        self.info.clicked.connect(self._toggle_details_pane)


        self._publish_history_model = SgPublishHistoryModel(self, self._task_manager)

        self._publish_history_model_overlay = ShotgunModelOverlayWidget(
            self._publish_history_model, self.history_view
        )

        self._publish_history_proxy = QtGui.QSortFilterProxyModel(self)
        self._publish_history_proxy.setSourceModel(self._publish_history_model)

        # now use the proxy model to sort the data to ensure
        # higher version numbers appear earlier in the list
        # the history model is set up so that the default display
        # role contains the version number field in shotgun.
        # This field is what the proxy model sorts by default
        # We set the dynamic filter to true, meaning QT will keep
        # continously sorting. And then tell it to use column 0
        # (we only have one column in our models) and descending order.
        self._publish_history_proxy.setDynamicSortFilter(True)
        self._publish_history_proxy.sort(0, QtCore.Qt.DescendingOrder)

        self.history_view.setModel(self._publish_history_proxy)

        self._history_delegate = SgPublishHistoryDelegate(
            self.history_view, self._status_model, self._action_manager
        )
        self.history_view.setItemDelegate(self._history_delegate)

        # event handler for when the selection in the history view is changing
        # note! Because of some GC issues (maya 2012 Pyside), need to first establish
        # a direct reference to the selection model before we can set up any signal/slots
        # against it
        self._history_view_selection_model = self.history_view.selectionModel()
        self._history_view_selection_model.selectionChanged.connect(
            self._on_history_selection
        )

        self._multiple_publishes_pixmap = QtGui.QPixmap(
            ":/res/multiple_publishes_512x400.png"
        )


        self.detail_playback_btn.clicked.connect(self._on_detail_version_playback)
        self._current_version_detail_playback_url = None

        # set up right click menu for the main publish view
        self._refresh_history_action = QtGui.QAction("Refresh", self.history_view)
        self._refresh_history_action.triggered.connect(
            self._publish_history_model.async_refresh
        )
        self.history_view.addAction(self._refresh_history_action)
        self.history_view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        # if an item in the list is double clicked the default action is run
        self.history_view.doubleClicked.connect(self._on_history_double_clicked)
        self._default_details_panel()

    def rescan(self):
        if self.interactive:
            self.model = MultiModel(parent=self)
            self.proxy_model.setSourceModel(self.model)
            self.log_window.clear()
            self.model.refresh()
            self.app.initialize_data()
        else:
            logger.info("Interactivity is disabled temporarily ")

    def setup_events(self):
        pass
        # self._do.clicked.connect(self.start_sync)

    def toggle_perforce_log(self):

        """
        Description:
            Hides/unhides the perforce log in the sync app UI
        """
        if self.interactive:
            if not self.log_window.isVisible():
                self.log_window.setVisible(True)

            else:
                self.log_window.setVisible(False)
        else:
            logger.info("Interactivity is disabled temporarily ")

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

    def update_progress_bar(self, val):
        if val < 0 or val >= 1:
            self._progress_bar.setVisible(False)
            self._progress_bar.setValue(0)
            self._global_progress_bar.setVisible(False)
            self._global_progress_bar.setValue(0)
        else:
            self._progress_bar.setVisible(True)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(val * 100)

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

    def _toggle_details_pane(self):
        """
        Executed when someone clicks the show/hide details button
        """
        if self.interactive:
            if self.container_widget.isVisible():
                self._set_details_pane_visiblity(False)
            else:
                self._set_details_pane_visiblity(True)
        else:
            logger.info("Interactivity is disabled temporarily ")

    def _set_details_pane_visiblity(self, visible):
        """
        Specifies if the details pane should be visible or not
        """
        # store our value in a setting
        # self._settings_manager.store("show_details", visible)
        if self.interactive:
            if visible == False:
                # hide details pane
                self._details_pane_visible = False
                self.container_widget.setVisible(False)
                self.info.setText("Show Details")

            else:
                # show details pane
                self._details_pane_visible = True
                self.container_widget.setVisible(True)
                self.info.setText("Hide Details")

                # if there is something selected, make sure the detail
                # section is focused on this
                if self._key:
                    self._setup_details_panel(self._key, self._id)
                else:
                    self._default_details_panel()

            # logger.info("key is: {}, id is {}".format(self._key, self._id))
            self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        else:
            logger.info("Interactivity is disabled temporarily ")


    def _get_sg_data_dict(self, key, id):
        """
        Get SG Publish Dict
        """
        sg_data_dict = {}
        if key:
            filters = [["sg_p4_depo_path", "in", [key]]]
            fields = ['code', 'created_at', 'created_by', 'created_by.HumanUser.image', 'description',
                      'entity', 'id', 'image', 'name', 'path', 'project', 'published_file_type',
                      'sg_status_list', 'task', 'task.Task.content', 'task.Task.due_date',
                      'task.Task.sg_status_list', 'task_uniqueness', 'type', 'version',
                      'version.Version.sg_status_list', 'version_number', "task.Task.step.Step.code"]
            order = [{'field_name': 'version_number', 'direction': 'desc'}]
            sg_data_dict = self._sg.find_one('PublishedFile', filters, fields, order)
        """
        logger.info("key: {}".format(key))
        logger.info("sg_data_dict is:")
        if sg_data_dict:
            for k, v in sg_data_dict.items():
                logger.info("{}: {}".format(k, v))
        """

        return sg_data_dict

    def _default_details_panel(self):
        self._publish_history_model.clear()
        self.details_header.setText("")
        #self.details_image.setPixmap(self._no_selection_pixmap)
        self.details_image.setPixmap(self._no_selection_pixmap.scaled(
            self.details_image.width(), self.details_image.height(), QtCore.Qt.KeepAspectRatio))

    def _setup_details_panel(self, key, id):
        """
        Sets up the details panel with info for a given item.
        """

        def __make_table_row(left, right):
            """
            Helper method to make a detail table row
            """
            return (
                    "<tr><td><b style='color:#2C93E2'>%s</b>&nbsp;</td><td>%s</td></tr>"
                    % (left, right)
            )

        def __set_publish_ui_visibility(is_publish):
            """
            Helper method to enable disable publish specific details UI
            """
            # disable version history stuff
            self.version_history_label.setEnabled(is_publish)
            self.history_view.setEnabled(is_publish)

            # hide actions and playback stuff
            self.detail_actions_btn.setVisible(is_publish)
            self.detail_playback_btn.setVisible(is_publish)

        def __clear_publish_history(pixmap):
            """
            Helper method that clears the history view on the right hand side.

            :param pixmap: image to set at the top of the history view.
            """
            self._publish_history_model.clear()
            self.details_header.setText("")
            self.details_image.setPixmap(QtGui.QPixmap(self._no_pubs_found_icon).scaled(
                self.details_image.width(), self.details_image.height(), QtCore.Qt.KeepAspectRatio))

            __set_publish_ui_visibility(False)

        # note - before the UI has been shown, querying isVisible on the actual
        # widget doesn't work here so use member variable to track state instead
        if not self._details_pane_visible:
            return

        if not key:
            #__clear_publish_history(self._no_selection_pixmap)
            __clear_publish_history(self._no_pubs_found_icon)

            logger.info("Unable to find the item in SG data. Item may not be published.")

            # an item which doesn't have any sg data directly associated
            # typically an item higher up the tree
            # just use the default text
            """
            if "name" in sg_data_dict:
                folder_name = __make_table_row("Name", sg_data_dict.get("name"))
                self.details_header.setText("<table>%s</table>" % folder_name)
                __set_publish_ui_visibility(False)
            """

        if key:
            sg_data_dict = self._get_sg_data_dict(key, id)
            if not sg_data_dict:
                __clear_publish_history(self._no_pubs_found_icon)
                msg = "Unable to find the item in SG data. Item may not be published."
                logger.info(msg)
                self.add_log(msg)

            else:
                # this is a publish!
                __set_publish_ui_visibility(True)

                if "image" in sg_data_dict:
                    try:
                        image_url = sg_data_dict.get("image")
                        file_path = "{}/tmp.png".format(self.dir_path)
                        urllib.request.urlretrieve(image_url, file_path)
                        #self.details_image.setPixmap(QtGui.QPixmap(file_path))
                        self.details_image.setPixmap(QtGui.QPixmap(file_path).scaled(
                            self.details_image.width(), self.details_image.height(), QtCore.Qt.KeepAspectRatio))
                        # msg = "Saving temp image file: {}".format(file_path)
                        # logger.info(msg)
                        # self.log_window.append(msg)
                    except:
                        logger.info("Unable to display thump pixmap")
                        pass

                sg_item = sg_data_dict

                # sort out the actions button
                actions = self._action_manager.get_actions_for_publish(
                    sg_item, self._action_manager.UI_AREA_DETAILS
                )
                if len(actions) == 0:
                    self.detail_actions_btn.setVisible(False)
                else:
                    self.detail_playback_btn.setVisible(True)
                    self._details_action_menu.clear()
                    for a in actions:
                        self._dynamic_widgets.append(a)
                        self._details_action_menu.addAction(a)

                # if there is an associated version, show the play button
                if sg_item.get("version"):
                    sg_url = sgtk.platform.current_bundle().shotgun.base_url
                    url = "%s/page/media_center?type=Version&id=%d" % (
                        sg_url,
                        sg_item["version"]["id"],
                    )

                    self.detail_playback_btn.setVisible(True)
                    self._current_version_detail_playback_url = url

                else:
                    self.detail_playback_btn.setVisible(False)
                    self._current_version_detail_playback_url = None

                if sg_item.get("name") is None:
                    name_str = "No Name"
                else:
                    name_str = sg_item.get("name")

                # type_str = shotgun_model.get_sanitized_data(
                #    #item, SgLatestPublishModel.PUBLISH_TYPE_NAME_ROLE
                #    sg_item.get("type"), SgLatestPublishModel.PUBLISH_TYPE_NAME_ROLE
                # )

                if "published_file_type" in sg_item and "name" in sg_item["published_file_type"]:
                    type_str = sg_item["published_file_type"]["name"]
                else:
                    type_str = sg_item.get("type")
                msg = ""
                msg += __make_table_row("Name", name_str)
                msg += __make_table_row("Type", type_str)

                version_number = sg_item.get("version_number")
                vers_str = "%03d" % version_number if version_number is not None else "N/A"

                msg += __make_table_row("Version", "%s" % vers_str)

                if sg_item.get("entity"):
                    display_name = shotgun_globals.get_type_display_name(
                        sg_item.get("entity").get("type")
                    )
                    entity_str = "<b>%s</b> %s" % (
                        display_name,
                        sg_item.get("entity").get("name"),
                    )
                    msg += __make_table_row("Link", entity_str)
                # sort out the task label
                if sg_item.get("task"):

                    if sg_item.get("task.Task.content") is None:
                        task_name_str = "Unnamed"
                    else:
                        task_name_str = sg_item.get("task.Task.content")

                    if sg_item.get("task.Task.sg_status_list") is None:
                        task_status_str = "No Status"
                    else:
                        task_status_code = sg_item.get("task.Task.sg_status_list")
                        task_status_str = self._status_model.get_long_name(
                            task_status_code
                        )

                    msg += __make_table_row(
                        "Task", "%s (%s)" % (task_name_str, task_status_str)
                    )
                else:
                    task_name_str = "N/A"
                    msg += __make_table_row("Task", "%s" % task_name_str)


                # if there is a version associated, get the status for this
                if sg_item.get("version.Version.sg_status_list"):
                    task_status_code = sg_item.get("version.Version.sg_status_list")
                    task_status_str = self._status_model.get_long_name(task_status_code)
                else:
                    task_status_str = "N/A"
                msg += __make_table_row("Review", task_status_str)


                if sg_item.get("task.Task.step.Step.code"):
                    step = sg_item.get("task.Task.step.Step.code")
                    step_str = "%s" % step if step is not None else "N/A"
                else:
                    step_str = "N/A"
                msg += __make_table_row("Step", step_str)

                self.details_header.setText("<table>%s</table>" % msg)

                # tell details pane to load stuff
                # self.log('****** sg_data')
                # for k, v in sg_data_dict.items():
                #    self.log('{}: {}'.format(k, v))

                self._publish_history_model.load_data(sg_data_dict)

            self.details_header.updateGeometry()

    def on_item_clicked(self, index):
        """
        Single click on tree item
        """
        key, id = None, 0

        if self.interactive:

            # map from the SortFilterProxy item to the original model pointer, get Row item from it
            pointer_to_source_item = self.proxy_model.mapToSource(
                index
            ).internalPointer()

            # get index of the column
            path_index = pointer_to_source_item.schema.key_index_map.get("item_found")
            if path_index:
                # retrieve the path for that item on the given index
                client_file = pointer_to_source_item.rowData[path_index]

                """
                key = key[2:]
                key.replace("/", "\\")
                key = "/{}".format(key)
                """

                if client_file in self._row_data:
                    key = self._row_data[client_file]
                    logger.info(">>>>>> key: {}".format(client_file))

            if key:
                msg = "Displaying details of file: {}".format(key)
            else:
                msg = "Publish data is not available for this item"
            self.add_log(msg)

            self._key = key
            self._id = id
            self._setup_details_panel(key, id)
        else:
            logger.info("Interactivity is disabled temporarily ")


    def _on_history_selection(self, selected, deselected):
        """
        Called when the selection changes in the history view in the details panel

        :param selected:    Items that have been selected
        :param deselected:  Items that have been deselected
        """
        # emit the selection_changed signal
        # self.selection_changed.emit()

    def _on_detail_version_playback(self):
        """
        Callback when someone clicks the version playback button
        """
        # the code that sets up the version button also populates
        # a member variable which olds the current media center url.
        if self.interactive:
            msg = "Playing back selected history file ..."
            self.add_log(msg)
            if self._current_version_detail_playback_url:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(self._current_version_detail_playback_url)
                )
        else:
            logger.info("Interactivity is disabled temporarily ")

    def _on_history_double_clicked(self, model_index):
        """
        When someone double clicks on a publish in the history view, run the
        default action

        :param model_index:    The model index of the item that was double clicked
        """
        if self.interactive:
            # the incoming model index is an index into our proxy model
            # before continuing, translate it to an index into the
            # underlying model
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)

            # now we have arrived at our model derived from StandardItemModel
            # so let's retrieve the standarditem object associated with the index
            item = source_index.model().itemFromIndex(source_index)

            # Run default action.
            sg_item = shotgun_model.get_sg_data(model_index)
            default_action = self._action_manager.get_default_action_for_publish(
                sg_item, self._action_manager.UI_AREA_HISTORY
            )
            if default_action:
                default_action.trigger()
        else:
            logger.info("Interactivity is disabled temporarily ")

    def open_context_menu(self, point):
        if self.interactive:
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
        else:
            logger.info("Interactivity is disabled temporarily ")

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

        if self.interactive:
            for filter_type in self.list_of_filter_types:
                if hasattr(self, "_{}_actions".format(filter_type)):
                    actions = getattr(self, "_{}_actions".format(filter_type))
                    if actions:
                        for checkbox in actions.values():

                            checkbox.setChecked(True)
            self.filter_triggered()
        else:
            logger.info("Interactivity is disabled temporarily ")

    def filter_triggered(self):
        """
        Description:
            description here
        """
        if self.interactive:

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
        else:
            logger.info("Interactivity is disabled temporarily ")


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
        if self.interactive:
            logging.debug("Refreshing UI based on changes")
            # if self.interactive:
            self.model.refresh()
        else:
            logger.info("Interactivity is disabled temporarily ")

    def show_tree(self):
        self.view_stack.setCurrentWidget(self.tree_view)

    def show_waiting(self):
        self.view_stack.setCurrentWidget(self.b)

    def closeEvent(self, event):
        """
        Executed when the main dialog is closed.
        All worker threads and other things which need a proper shutdown
        need to be called here.
        """
        # display exit splash screen
        """
        splash_pix = QtGui.QPixmap(":/res/exit_splash.png")
        splash = QtGui.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
        """
        QtCore.QCoreApplication.processEvents()

        try:
            # clear the selection in the main views.
            # this is to avoid re-triggering selection
            # as items are being removed in the models
            #self.ui.history_view.selectionModel().clear()
            #self.ui.publish_view.selectionModel().clear()

            # disconnect some signals so we don't go all crazy when
            # the cascading model deletes begin as part of the destroy calls

            # gracefully close all connections
            shotgun_globals.unregister_bg_task_manager(self._task_manager)
            self._task_manager.shut_down()

            # remove temp image directory
            shutil.rmtree(self.dir_path)

        except:
            app = sgtk.platform.current_bundle()
            app.log_exception("Error running Loader App closeEvent()")


        # okay to close dialog
        event.accept()


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

#from . import resources_rc
