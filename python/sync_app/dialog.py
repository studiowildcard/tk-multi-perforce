# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import threading

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog
from .main import SyncApp

# standard toolkit logger
logger = sgtk.platform.get_logger(__name__)


def show_dialog(app_instance, entities=None, specific_files=None):
    """
    Shows the main dialog window.
    """
    # in order to handle UIs seamlessly, each toolkit engine has methods for launching
    # different types of windows. By using these methods, your windows will be correctly
    # decorated and handled in a consistent fashion by the system.

    # we pass the dialog class to this method and leave the actual construction
    # to be carried out by toolkit.

    logger.info(str(entities))
    app = SyncApp(app_instance, entities=entities, specific_files=specific_files)
    ui = app.ui_class

    return app_instance.engine.show_modal(
        "Perforce Sync",
        app_instance,
        ui.get("class"),
        *ui.get("args"),
        **ui.get("kwargs"),
    )
 # show_dialog(
        #     app,
        #     [
        #         {"type": "Asset", "id": 4554},
        #         {"type": "Asset", "id": 6166},
        #         {"type": "Asset", "id": 6829},
        #     ],
        #     specific_files,
        # )

def open_sync_files_dialog(app, entity_type=None, entity_ids=None):
    """
    Prepare assets to send to the P4 Sync window to process.
    """
    try:
        specific_files = False
        entities_to_sync = []

        # Synchronize filesystem structure
        synclog = app.engine.sgtk.synchronize_filesystem_structure()
        # app.log_debug(f"Synced Folders: {synclog}")

        # Process entities based on the provided type
        if entity_type:
            if entity_type == "Task":
                tasks = app.shotgun.find(
                    entity_type, [["id", "in", entity_ids]], ["entity"]
                )
                entities_to_sync = entities_from_tasks(app, tasks)
            elif entity_type == "Asset":
                ids = []
                assets = app.shotgun.find(
                    entity_type, [["id", "in", entity_ids]], ["sg_asset_parent", "code"]
                )
                ids.extend(
                    [i.get("id") for i in assets if not i.get("sg_asset_parent")]
                )
                entities_to_sync = [
                    {"type": entity_type, "id": id} for id in list(set(ids))
                ]
            elif entity_type == "PublishedFile":
                specific_files = True
                pfiles = app.shotgun.find(
                    entity_type,
                    [["id", "in", entity_ids]],
                    ["entity", "path_cache", "path"],
                )
                entities_to_sync = pfiles
            else:
                entities_to_sync = [
                    {"type": entity_type, "id": id} for id in entity_ids
                ]
        else:
            # Default behavior: fetch user's tasks if no specific context
            user = app.context.user
            user_tasks = app.context.sgtk.shotgun.find(
                "Task",
                [
                    ["task_assignees", "is", user],
                    ["project", "is", app.context.project],
                    ["sg_status_list", "in", ["rdy", "ip"]],
                ],
                ["entity", "sg_status_list"],
            )
            entities_to_sync = entities_from_tasks(app, user_tasks)

        # Import the framework using the app instance to avoid errors
        try:
            p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
            # p4 = p4_fw.connection.connect()

        except Exception as e:
            logger.error("Failed to import tk-framework-perforce module. Check if the framework is properly installed and configured.")

            return


        # Call show_dialog with the processed entities
        show_dialog(app, entities_to_sync, specific_files)
    except Exception:
        import traceback
        app.log_error("Failed to Open Sync dialog!")
        app.log_error(traceback.format_exc())



def entities_from_tasks(app, tasks):
    entities_to_sync = []
    uids = []
    if tasks:
        for task in tasks:
            linked_entity = task.get("entity")
            if linked_entity:
                uid = "{}_{}".format(linked_entity.get("type"), linked_entity.get("id"))

                if linked_entity.get("type") in [
                    "Asset",
                    "Sequence",
                    "Shot",
                    "CustomEntity01",
                ]:
                    ids = []
                    assets = []
                    env_asset = None
                    # Since we'll be iterating through possible asset relations below, keep a uid of type/id
                    # so we can ensure we have item novelty
                    if uid not in uids:
                        uids.append(uid)

                    # assuming coverage for the above list of types is provided in the resolver, add the linked_entity
                    entities_to_sync.append(linked_entity)

                    # Asset
                    if linked_entity.get("type") == "Asset":
                        assets = app.shotgun.find(
                            linked_entity.get("type"),
                            [["id", "in", [linked_entity.get("id")]]],
                            ["sg_asset_parent"],
                        )

                    # Shot
                    elif linked_entity.get("type") == "Shot":
                        shot = app.shotgun.find_one(
                            "Shot",
                            [["id", "in", [linked_entity.get("id")]]],
                            ["sg_sequence.Sequence.assets"],
                        )
                        if shot.get("sg_sequence.Sequence.assets"):
                            asset_ids = [
                                i.get("id")
                                for i in shot.get("sg_sequence.Sequence.assets")
                            ]
                            assets = app.shotgun.find(
                                "Asset", [["id", "in", asset_ids]], ["sg_asset_parent"]
                            )

                    # Sequence
                    elif linked_entity.get("type") == "Sequence":
                        seq = app.shotgun.find_one(
                            "Sequence",
                            [["id", "in", [linked_entity.get("id")]]],
                            ["assets"],
                        )
                        if seq.get("assets"):
                            assets = app.shotgun.find(
                                "Asset",
                                [
                                    [
                                        "id",
                                        "in",
                                        [i.get("id") for i in seq.get("assets")],
                                    ]
                                ],
                                ["sg_asset_parent"],
                            )

                    # identify the parent asset if one exists
                    ids.extend(
                        [
                            i.get("sg_asset_parent").get("id")
                            for i in assets
                            if i.get("sg_asset_parent")
                        ]
                    )
                    ids.extend(
                        [i.get("id") for i in assets if not i.get("sg_asset_parent")]
                    )

                    # add all assets discovered if uid key not already in the dict.
                    for id in list(set(ids)):
                        uid = "{}_{}".format("Asset", id)
                        if uid not in uids:
                            uids.append(uid)
                            entities_to_sync.append({"type": "Asset", "id": id})

    return entities_to_sync
