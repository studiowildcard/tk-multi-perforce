from urllib import response
from webbrowser import get
import sgtk
from sgtk.platform.qt import QtCore, QtGui

import os
import traceback
import pprint
import random
import time
import uuid
import copy


from ..process.template_resolver import TemplateResolver
from ..utils.inspection import method_decorator, trace

logger = sgtk.platform.get_logger(__name__)


class SyncSignaller(QtCore.QObject):
    """
    Create signaller class for Sync Worker, required for using signals due to QObject inheritance
    """

    started = QtCore.Signal(dict)
    finished = QtCore.Signal()
    completed = QtCore.Signal(dict)  # (path to sync, p4 sync response)


class AssetInfoGatherSignaller(QtCore.QObject):
    """
    Create signaller class for AssetInfoGather Worker, required for using signals due to QObject inheritance
    """

    progress = QtCore.Signal(str)
    root_path_resolved = QtCore.Signal(str)
    info_gathered = QtCore.Signal(dict)
    item_found_to_sync = QtCore.Signal(dict)
    status_update = QtCore.Signal(str)
    includes = QtCore.Signal(tuple)
    gathering_complete = QtCore.Signal(dict)
    total_items_found = QtCore.Signal(dict)
    p4_log_received = QtCore.Signal(dict)  # this is for p4 raw data log


# @method_decorator(trace)
class SyncWorker(QtCore.QRunnable):

    # structurally anticipate basic p4 calls, which will route to the main form.
    p4 = None

    path_to_sync = None
    asset_name = None
    item = None

    def __init__(self):
        """
        Handles syncing specific file from perforce depot to local workspace on disk
        """
        super(SyncWorker, self).__init__()
        self.signaller = SyncSignaller()

        # use signals from Signaller, since we cant in a non-QObject derrived
        # object like this QRunner.
        self.started = self.signaller.started
        self.finished = self.signaller.finished
        self.completed = self.signaller.completed

    def log_error(self, e):
        self.fw.log_error(str(e))
        self.fw.log_error(traceback.format_exc())

    @QtCore.Slot()
    def run(self):

        """
        Run syncs from perforce, signals information back to main thread.
        """
        try:

            self.started.emit({"model_item": self.id})

            self.p4 = self.fw.connection.connect()
            logger.debug("P4 CONNECTION ESTABLISHED: {}".format(self.p4))

            # # run the syncs
            #logger.debug("THIS IS PATH_TO_SYNC: {}".format(self.path_to_sync))

            p4_response = self.p4.run("sync", "-f", "{}#head".format(self.path_to_sync))
            # logger.debug("THIS IS P4_RESPONSE: {}".format(p4_response))

            # emit item key and p4 response to main thread

            self.completed.emit({"model_item": self.id, "path": self.path_to_sync})

        except Exception as e:
            import traceback

            self.completed.emit(
                {
                    "model_item": self.id,
                    "path": self.path_to_sync,
                    "error": traceback.format_exc(),
                }
            )


# @method_decorator(trace)
class AssetInfoGatherWorker(QtCore.QRunnable):
    def __init__(self, app=None, entity=None, framework=None):
        """
        Handles gathering information about specific asset from SG and gets related Perforce information
        """
        super(AssetInfoGatherWorker, self).__init__()

        self.id = str(uuid.uuid4())

        self.app = app
        self.entity = entity

        self.force_sync = False

        self.asset_map = {}

        self._items_to_sync = []
        self._status = None
        self._icon = None
        self._detail = None

        self.fw = framework
        self.asset_item = None  # this is expected to be a dictionary

        self.progress_batch_size = 0
        self.progress_batch_completion = 0

        self.signaller = AssetInfoGatherSignaller()

        self.info_gathered = self.signaller.info_gathered
        self.progress = self.signaller.progress
        self.root_path_resolved = self.signaller.root_path_resolved
        self.item_found_to_sync = self.signaller.item_found_to_sync
        #self.sg_data_found_to_sync = self.signaller.sg_data_found_to_sync
        self.status_update = self.signaller.status_update
        self.includes = self.signaller.includes
        self.total_items_found = self.signaller.total_items_found
        self.gathering_complete = self.signaller.gathering_complete

        self.p4_log_received = self.signaller.p4_log_received  # raw p4 log

        self.publish_file = False

        self.spec_file = os.path.join(os.path.expanduser("~"), "p4spec.txt")

    def log_error(self, e):
        self.fw.log_error(str(e))
        self.fw.log_error(traceback.format_exc())

    @property
    def asset_name(self):

        name = None
        if self.asset_item.get("context"):
            name = self.asset_item.get("context").entity.get("name")
        if not name:
            if self.entity.get("code"):
                name = self.entity.get("code")
            else:
                name = self.app.shotgun.find_one(
                    self.entity.get("type"),
                    [["id", "is", self.entity.get("id")]],
                    ["code"],
                ).get("code")

        if self.entity.get("type") in ["PublishFiles"]:
            sg_ret = self.app.shotgun.find_one(
                "Asset",
                [["id", "is", self.entity.get("entity").get("id")]],
                ["code"],
            )
            name = sg_ret.get("code")
        return name

    @property
    def root_path(self):
        rp = self.asset_item.get("root_path")
        if self.entity.get("type") in ["PublishedFile"]:
            # TODO: this needs to become dynamic
            rp = "B:/" + self.entity.get("path_cache")
        return rp

    @property
    def status(self):
        if self.asset_item.get("error"):
            self._icon = "warning"
            self._status = "Error"
            self._detail = self.asset_item.get("error")
        return self._status

    def collect_and_map_info(self):
        """
        Call perforce for response and form data we will signal back
        """

        if self.status != "error":
            self.get_perforce_sync_dry_reponse()

        # payload that we'll send back to the main thread to make UI item with
        self.info_to_signal = {
            "asset_name": self.asset_name,
            "root_path": self.root_path,
            "status": self._status,
            "details": self._detail,
            "icon": self._icon,
            "asset_item": self.asset_item,
            "items_to_sync": self._items_to_sync,
        }

        #logger.debug("These are items to sync: {}".format(self._items_to_sync))

    def write_spec_file(self, contents):
        with open(self.spec_file, "w") as spec_file:
            spec_file.writelines(contents)

    def get_perforce_sync_dry_reponse(self):
        """
        Get a response from perforce about our wish to sync a specific asset root path,
        Contextually use response to drive our status that we show the user.
        """
        logger.debug("DRY RESPONSE RAN!")

        if self.root_path and (self.entity.get("type") not in ["PublishedFile"]):

            self.p4 = self.fw.connection.connect()

            arguments = ["-n"]
            if self.force:
                arguments.append("-f")
            sync_response = self.p4.run("sync", *arguments, self.root_path + "#head")

            # Keys in dictionary is: depotFile,clientFile,rev,action,fileSize

            if isinstance(sync_response, list):
                for x in sync_response:
                    self.p4_log_received.emit(x)

            if not sync_response:
                self._status = "Not In Depot"
                self._icon = "error"
                self._detail = "Nothing in depot resolves [{}]".format(self.root_path)

            elif len(sync_response) is 1 and type(sync_response[0]) is str:
                self._status = "Syncd"
                self._icon = "success"
                self._detail = "Nothing new to sync for [{}]".format(self.root_path)
            else:
                # if the response from p4 has items... make UI elements for them
                self._items_to_sync = [i for i in sync_response if type(i) != str]
                self._status = "{} items to Sync".format(len(self._items_to_sync))
                self._icon = "load"
                self._detail = self.root_path

        if self.entity.get("type") in ["PublishedFile"]:
            self._items_to_sync = [
                {"clientFile": "B:/" + self.entity.get("path_cache")}
            ]
            self._status = "Exact Path"
            self._detail = "Exact path specified: [{}]".format(self.root_path)
            self._icon = "load"

    @QtCore.Slot()
    def run(self):

        """
        Checks if there are errors in the item, signals that, or if not, gets info regarding what there is to sync.
        """

        try:

            self.template_resolver = TemplateResolver(
                app=self.app, entity=self.entity, p4=self.p4
            )

            self.asset_item = self.template_resolver.entity_info
            progress_status_string = ""

            self.status_update.emit(
                "Requesting sync information for {}".format(self.asset_name)
            )

            self.fw.log_info(self.asset_item)
            self.collect_and_map_info()

            if self.status == "Syncd":
                progress_status_string = " (Nothing to sync. Skipping...)"
            # self.log_error(str(self._items_to_sync))
            if self.status != "Error":

                if self._items_to_sync:
                    items_count = len(self._items_to_sync)

                    logger.info("Emitting info")
                    self.total_items_found.emit(
                        {"id": -1, "count": items_count}
                    )
                    # make lookup list for SG api call for published files to correlate.
                    depot_files = [i.get("depotFile") for i in self._items_to_sync]
                    find_fields = [
                        "sg_p4_change_number",
                        "code",
                        "entity.Asset.code",
                        "sg_p4_depo_path",
                        "task.Task.step.Step.code",
                        "published_file_type.PublishedFileType.code",
                        "id"
                    ]

                    # if we want to look for results PER depot file, we look against the list
                    sg_filter = ["sg_p4_depo_path", "in", depot_files]

                    # if the entity itself is a PublishedFile, use it's ID
                    if self.entity.get("type") in ["PublishedFile"]:
                        sg_filter = ["id", "in", self.entity.get("id")]
                    logger.info("Getting published files")
                    # get PublishedFile information needed, as configured above with fields and filters
                    published_files = self.app.shotgun.find(
                        "PublishedFile", [sg_filter], find_fields
                    )
                    logger.info("Done, getting published files")
                    # make dictionary of items callable by key: sg_p4_depot_path
                    published_file_by_depot_file = {
                        i.get("sg_p4_depo_path"): i for i in published_files
                    }
                    logger.info("Done, getting published files by depot")
                    # self.fw.log_info(published_file_by_depot_file)

                    for j, item in enumerate(self._items_to_sync):
                        #logger.info("{}: Items count: {}".format(j, items_count))
                        if j % 50 == 0 or j == items_count-1:
                            self.total_items_found.emit(
                                {"id": j, "count": items_count}
                            )

                        published_file = published_file_by_depot_file.get(
                            item.get("depotFile")
                        )

                        for i in self.asset_map.keys():

                            # self.log_error(i)
                            # self.log_error(item.get("clientFile"))
                            if i in item.get("clientFile"):
                                self.asset_item = self.asset_map[i]["asset"]
                                self.entity = self.asset_map[i]["entity"]

                        # step = None # grab step here
                        ext = None
                        step = None
                        file_type = None
                        id = 0

                        if published_file:
                            id = published_file.get('id')

                            step = published_file.get("task.Task.step.Step.code")
                            if step:
                                self.includes.emit(("step", step))

                            file_type = published_file.get(
                                "published_file_type.PublishedFileType.code"
                            )
                            if file_type:
                                self.includes.emit(("type", file_type))

                            ext = None

                        if "." in item.get("clientFile"):
                            ext = os.path.basename(item.get("clientFile")).split(".")[
                                -1
                            ]
                            self.includes.emit(("ext", ext.lower()))

                        status = item.get("action")
                        if self.entity.get("type") in ["PublishedFile"]:
                            status = "Exact File"
                        self.item_found_to_sync.emit(
                            {
                                "worker_id": self.id,
                                "asset_name": self.asset_name,
                                "item_found": item,
                                "step": step,
                                "type": file_type,
                                "ext": ext.lower(),
                                "status": status,
                                "id": id,
                                "index": j
                            }
                        )
                else:
                    #self.total_items_found.emit({"id": self.id, "count": 1})
                    self.item_found_to_sync.emit(
                        {
                            "worker_id": self.id,
                            "asset_name": self.asset_name,
                            "status": "Everything sync'd",
                        }
                    )
            else:
                progress_status_string = " (Encountered error. See details)"
            # self.fw.log_info(progress_status_string)

        except Exception as e:
            import traceback

            self.log_error(traceback.format_exc())

        self.info_gathered.emit({"status": "gathered"})
