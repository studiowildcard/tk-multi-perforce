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
        self.threadpool.start(self.timer_worker)
        self.threadpool.setMaxThreadCount(min(23, self.threadpool.maxThreadCount()))
        self.model_view_updating = False

        # file base for accessing Qt resources outside of resource scope
        self.basepath = os.path.dirname(os.path.abspath(__file__))

        self.entities_to_sync = entities

        self.input_data = self.entities_to_sync
        # TODO why create another variable here rather than just using the one we have?

        self.row_data = {}
        self.row = 0
        self._total = 0
        self.current_entity_index = 0
        self.current_count = 0

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

        self._app = QtGui.QApplication(sys.argv)
        ui = Ui_Dialog(self.parent, self)
        ui.show()
        self._app.exec_()

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

        msg = "\n\n"
        self.ui.add_log(msg)

        self.ui._do.clicked.connect(self.start_sync)

        self.ui.interactive = True

        self.logger.info("App build completed with workers")
        # msg = "App build completed with workers"
        # self.ui.add_log(msg)

    def report_progress(self, item):
        progress_sum = 0
        self.entity_total = item.get("count", 0)
        current_index = item.get("id", 0)
        current_index += 1

        if self._total > 0:
            progress_sum = self.current_entity_index/self._total
            if self.entity_total > 0:
                progress_sum += (current_index / self.entity_total) / self._total
        # self.logger.info(">>> current: {}, total: {}, sum: {}".format(current_index, self.entity_total, progress_sum))
        if current_index == 0:
            if self.entity_total < 1000:
                msg = "\nInitializing data for entity ...\n"
            else:
                msg = "\nInitializing data for entity. This may take few seconds ...\n"
            self.ui.add_log(msg)

        self.ui.update_progress_bar(progress_sum)


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

        index = item.get("index", 0)
        index += 1
        if "item_found" in item:
            key = item["item_found"].get("clientFile", None)
            val = item["item_found"].get("depotFile", None)
            # self.logger.info("key : {}".format(key))
            # self.logger.info("val : {}".format(val))
            self.row_data[key] = val
            self.ui.get_row_data(self.parent_sgtk_app, self.row_data)

            msg = "({}/{}) Adding file: {}".format(index, self.entity_total, key)
            self.ui.add_log(msg)

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
        #self.progress_handler.iterate("assets_info")
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

        #if not self.ui.progress_handler:
        #    self.ui.progress_handler = self.progress_handler

        #self.progress_handler.track_progress(
        #    **{"items": len(self.entities_to_sync), "id": "assets_info"}
        #)

        for index, current_entity in enumerate(self.entities_to_sync):
            self.current_entity_index = index
            asset_info_gather_worker = AssetInfoGatherWorker(
                app=self.parent_sgtk_app, entity=current_entity, framework=self.fw
            )

            asset_info_gather_worker.force = self.ui._force_sync.isChecked()
            asset_info_gather_worker.p4 = self.p4
            asset_info_gather_worker.total_items_found.connect(self.report_progress)
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

        self.ui.interactive = True

    def item_starting_sync(self, status_dict):
        self.ui.interactive = False
        # make sure that the item knows its syncing,
        item = self.item_map.get(status_dict.get("model_item"))
        item.syncing = True
        # self.ui.model.refresh()

    def item_completed_sync(self, status_dict):

        item = self.item_map.get(status_dict.get("model_item"))

        self.progress_handler.iterate("sync_workers")
        self.ui.update_progress()
        self.current_count += 1
        # self.logger.info(status_dict.get("path"))
        msg = "({}) Syncing: {} ...".format(self.current_count, status_dict.get("path"))
        self.ui.add_log(msg)

        item.syncing = False

        if status_dict.get("error"):
            item.error = status_dict["error"]
        else:
            item.syncd = True
            if status_dict.get("p4_data"):
                item.newrev = status_dict["p4_data"][0].get("rev")

        self.ui.interactive = True
        # self.ui.model.refresh()

    def start_sync(self):
        """
        Iterate through assets and their sync items to start workers for all paths that require syncs.
        Utilize a global threadpool to process
        """
        msg = "\n Syncing Files ...\n"
        self.ui.add_log(msg)

        self.ui.interactive = False

        if not self.ui.progress_handler:
            self.ui.progress_handler = self.progress_handler


        # hold a map to our items while they process
        self.item_map = {}

        workers = []
        for asset in self.ui.model.rootItem.childItems:
            for sync_item in asset.childItems:

                if sync_item.should_be_visible:
                    # log.debug("THIS IS SYNC_ITEM: {}".format(sync_item.data_in))
                    sync_worker = SyncWorker()

                    self.item_map[sync_item.id] = sync_item
                    sync_worker.id = sync_item.id

                    sync_worker.path_to_sync = sync_item.data(5)
                    sync_worker.asset_name = sync_item.parent().data(1).split(" ")[0]

                    sync_worker.fw = self.fw

                    sync_worker.started.connect(self.item_starting_sync)
                    sync_worker.completed.connect(self.item_completed_sync)

                    workers.append(sync_worker)

        queue_length = len(workers)
        self.progress_handler.queue = {}
        self.progress_handler.track_progress(
            **{"items": queue_length, "id": "sync_workers"}
        )
        for worker in workers:
            self.threadpool.start(worker)

        self.ui.interactive = True

        # msg = "Syncing is complete"
        # self.ui.add_log(msg)


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
        # self.ui.log_window.addItem(message)
        self.ui.add_log(message)

