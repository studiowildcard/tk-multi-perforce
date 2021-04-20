# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
General Perforce operations supported by the app
"""

import os
import sys

import sgtk


def check_out_current_scene(app):
    """
    The flow for this is:
    - Is the scene checked out already?  if it is then show dialog saying this
    - Is the scene check-out-able?  If not, tell the user why
    - Get latest and check-out.

    Future:
    - pop-up dialog offering to get latest dependencies first?
    - be able to save preferences to not show dialog again (how to edit those prefs?)
    """
    pass


def revert_scene_changes(app):
    """
    Is this the same as showing open files but with the specific file selected?

    Flow:
    - Is scene checked out? if not then show dialog saying this
    - If it is then prompt user "Are you sure you want to revert your changes and close this scene?", Revert, Cancel
    -- have checkbox (that gets remembered) prompting user to go straight to the file manager
    - If user reverts scene then should we show the file manager automatically or should there be a prompt?
    -- Revert should definitely close scene (no saving changes), revert and get latest on the reverted file..

    """
    pass


def sync_files(app, entity_type, entity_ids):

    assets = []
    parent_assets = []
    depo_paths = []

    if entity_type == "Task":
        assets = app.shotgun.find("Asset", [["tasks.Task.id", "in", entity_ids]], ["sg_asset_parent", "code"])

    if entity_type == "Asset":
        assets = app.shotgun.find("Asset", [['id', "in", entity_ids]], ["sg_asset_parent", "code"])

    if assets:
        for a in assets:
            if a.get("sg_asset_parent"):
                parent_assets.append(a["sg_asset_parent"])
            else:
                parent_assets.append(a)
    else:
        app.log_info("No valid assets were found.")

    if parent_assets:
        asset_root_templ = app.sgtk.templates["asset_root"]
        for pa in parent_assets:
            ctx = app.sgtk.context_from_entity(pa["type"], pa["id"])
            template_fields = ctx.as_template_fields(asset_root_templ)
            asset_root_path = asset_root_templ.apply_fields(template_fields, platform=sys.platform)
            client_asset_root_path = os.path.join(asset_root_path, "...")

            p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
            p4 = p4_fw.connection.connect()
            p4_fw.util = p4_fw.import_module("util")

            rsync = p4.run("sync", client_asset_root_path)
            if rsync:
                app.log_info("The following files were synced to your client workspace:")
                for r in rsync:
                    app.log_info(r["clientFile"])
            else:
                app.log_info("No files needed to be synced to your client workspace in:\n{}".format(client_asset_root_path))

    else:
        app.log_info("No valid parent assets were found.")
