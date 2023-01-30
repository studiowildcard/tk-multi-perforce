import os
import queue
import traceback
import pprint
import random
import time
import sys
import pprint


import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtCore, QtGui
from functools import partial

from .utils import PrefFile, open_browser
from .utils.inspection import partialclass, trace, method_decorator
from .ui.dialog import Ui_Dialog
from .utils.progress import ProgressHandler
from .workers.sync_worker import SyncWorker, AssetInfoGatherWorker
from .workers.timed_events import TimeLord

log = sgtk.platform.get_logger(__name__)

# @method_decorator(trace)
class SyncApp:

    _fw = None
    _p4 = None
    _ui = None

    progress = 0

    def __init__(
        self,
        parent_sgtk_app,
        entities=None,
        specific_files=None,
        parent=None,
        data=None,
    ):

        """
        Construction of sync app
        """
        self.parent = parent
        self.entities_to_sync = entities
        self.parent_sgtk_app = parent_sgtk_app

        self.progress_handler = ProgressHandler()

        self.workers = {"asset_info": AssetInfoGatherWorker, "sync": SyncWorker}
        self.shotgun_globals = sgtk.platform.import_framework(
            "tk-framework-shotgunutils", "shotgun_globals"
        )

        # the threadpool we send thread workers to.
        self.threadpool = QtCore.QThreadPool.globalInstance()

        # TODO self.threadpool.setMaxThreadCount(self.threadpool.maxThreadCount(10))
        self.timer_worker = TimeLord()
        self.timer_worker.update_ui.connect(self.timed_event_handler)

        self._max_thread_count = min(23, self.threadpool.maxThreadCount())

        self.threadpool.setMaxThreadCount(self._max_thread_count)

        # start scheduler timer
        self.threadpool.start(self.timer_worker)
        self.model_view_updating = False

        # file base for accessing Qt resources outside of resource scope
        self.basepath = os.path.dirname(os.path.abspath(__file__))

        self.entities_to_sync = entities

        self.input_data = self.entities_to_sync
        # TODO why create another variable here rather than just using the one we have?

    @property
    def logger(self):
        # TODO ensure that the logger actually logs with proper naming
        logger = sgtk.platform.get_logger(__name__)
        return logger

    @property
    def ui(self):
        if not self._ui:
            self._ui = self.ui_class
        return self._ui

    @ui.setter
    def ui(self, ui):
        self._ui = ui

    @property
    def ui_class(self):
        return {
            "class": Ui_Dialog,
            "args": [self.parent, self],
            "kwargs": {"logger": self.parent_sgtk_app.logger},
        }

    def run(self):
        """
        Assumes we arent handling the UI elsewhere, and want to launch it here.
        """
        import sys

        app = QtGui.QApplication(sys.argv)
        ui = Ui_Dialog(self.parent, self)
        ui.show()
        app.exec_()

    @property
    def p4(self):
        """
        Implement framework if doesnt currently exist,  return it if it does
        """
        if not self._p4:
            self._p4 = self.fw.connection.connect()
        return self._p4

    @property
    def fw(self):
        """
        Implement framework if doesnt currently exist,  return it if it does
        """
        if not self._fw:
            self._fw = sgtk.platform.get_framework("tk-framework-perforce")
        return self._fw

    def setup(self):
        """
        We defer the init so that the app can begin setting itself up when
        the UI is ready/built. This method is called by the app.

        """
        # self.ui.list_of_filter_types = ["step", "type", "ext"]

        self.initialize_data()

        self.ui._do.clicked.connect(self.start_sync)

        self.logger.info("App build completed with workers")

    def report_worker_info(self, item):
        """
        Method to process incoming dictionaries regarding items found
        to sync.  This is connected to the worker thread's singal
        emitter so it is triggered automatically.

        Args:
            item (dict): dictionary with P4/SG single file sync information
                        ...
                        asset_name: str
                        item_found
        Raises:
            sgtk.TankError: _description_
        """

        self.ui.model.add_row(item)

    def item_completed(self, data):

        self.logger.debug("")
        self.ui.model.add_row(data)
        # self.ui.model.refresh()
        # self.ui.reload_view()

    def timed_event_handler(self, key):

        if key == "model_view_update":
            if not self.ui.interactive:
                if self.model_view_updating != True:
                    self.model_view_updating = True
                    self.ui.model.refresh()
                    self.ui.tree_view.expandAll()
                    self.ui.tree_view.setAnimated(True)
                self.model_view_updating = False

    def data_gathering_complete(self, completion_dict: dict) -> None:
        """
        General app method to be utilized by worker threads so that they can
        report completion.

        Args:
            completion_dict (dict)
        """
        self.ui.show_tree()
        self._cur_progress += 1
        self.logger.info("Progress: {}/{}".format(self._cur_progress, self._total))
        self.progress_handler.iterate("assets_info")
        self.ui.update_progress()
        self.logger.info("Finished gathering data from perforce.")

        if self._cur_progress == self._total:
            self.ui.model.refresh()
            self.ui.interactive = True

    def initialize_data(self):
        """
        Iterate through tk-multi-perforce delivered list of asset information,
        Utilize a global threadpool to process workers to ask P4 server for what
        there is to sync for these.
        """
        self.ui.interactive = False

        self._total = len(self.entities_to_sync)
        self._cur_progress = 0

        if not self.ui.progress_handler:
            self.ui.progress_handler = self.progress_handler

        self.progress_handler.track_progress(
            **{"items": len(self.entities_to_sync), "id": "assets_info"}
        )

        for i in self.entities_to_sync:
            asset_info_gather_worker = AssetInfoGatherWorker(
                app=self.parent_sgtk_app, entity=i, framework=self.fw
            )

            asset_info_gather_worker.force = self.ui._force_sync.isChecked()
            asset_info_gather_worker.p4 = self.p4

            # as workers emit the item_found_to_sync, hit that method with the payload from it
            asset_info_gather_worker.item_found_to_sync.connect(self.report_worker_info)
            asset_info_gather_worker.info_gathered.connect(self.data_gathering_complete)
            asset_info_gather_worker.includes.connect(self.ui.update_available_filters)

            # TODO signal for the raw perforce log. for debugging
            asset_info_gather_worker.p4_log_received.connect(
                self.handle_raw_perforce_log
            )

            # this adds to the threadpool and runs the `run` method on the QRunner.
            self.threadpool.start(asset_info_gather_worker)

    def item_starting_sync(self, status_dict):
        # make sure that the item knows its syncing,
        item = self.item_map.get(status_dict.get("model_item"))
        item.syncing = True
        # self.ui.model.refresh()

    def item_completed_sync(self, status_dict):
        item = self.item_map.get(status_dict.get("model_item"))

        self.progress_handler.iterate("sync_workers")
        self.ui.update_progress()

        # self.logger.info(status_dict.get("path"))

        item.syncing = False

        if status_dict.get("error"):
            item.error = status_dict["error"]
        else:
            item.syncd = True

        # self.ui.model.refresh()

    def handle(self, info):
        self.logger.info(str(info))

    def start_sync(self):
        """
        Iterate through assets and their sync items to start workers for all paths that require syncs.
        Utilize a global threadpool to process
        """
        try:
            self.ui.interactive = False

            # hold a map to our items while they process
            self.item_map = {}

            paths_to_sync = []
            workers = []
            worker_path_batches = []
            path_count = 1
            for asset in self.ui.model.rootItem.childItems:

                for sync_item in asset.childItems:

                    if sync_item.should_be_visible:
                        # log.debug("THIS IS SYNC_ITEM: {}".format(sync_item.data_in))

                        self.item_map[sync_item.id] = sync_item
                        # sync_worker.id = sync_item.id
                        sync_request = {"id": sync_item.id, "path": sync_item.data(5)}
                        if int(float(sync_item.data(4))) > 500:
                            worker_path_batches.append([sync_request])
                        elif path_count < self._max_thread_count:
                            paths_to_sync.append(sync_request)
                            path_count += 1
                        else:
                            worker_path_batches.append(paths_to_sync)
                            paths_to_sync = [sync_request]
                            path_count = 1
            self.logger.info(str(worker_path_batches))
            worker_path_batches.append(paths_to_sync)
            queue_length = 0
            for batch in worker_path_batches:
                self.logger.info("Adding batch of paths to the sync worker to sync.")
                sync_worker = SyncWorker(self.fw, batch)
                sync_worker.started.connect(self.item_starting_sync)
                sync_worker.completed.connect(self.item_completed_sync)

                # connect progress-specific signals
                # sync_worker.p4.progress.description.connect(self.handle)

                queue_length += len(batch)

                # ±for worker in workers:

                self.threadpool.start(sync_worker)
            self.progress_handler.queue = {}
            self.progress_handler.track_progress(
                **{"items": queue_length, "id": "sync_workers"}
            )
        except Exception as e:
            self.logger.error(e)

    def handle_raw_perforce_log(self, perforce_data):
        """
        Description:
            Method to extract information and add it to the log UI in the sync app

        perforce_data -> Dict:
            raw data extracted from perforce
        """
        if isinstance(perforce_data, dict):
            depotfile = perforce_data.get("depotFile")
            change = perforce_data.get("change")
            message = "depotfile: {}  |  Change: {}".format(depotfile, change)

        elif isinstance(perforce_data, str):
            message = perforce_data
        self.ui.log_window.addItem(message)
