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




def open_sync_files_dialog(app, entity_type=None,  entity_ids=None):
    """
    Show the Perforce sync dialog
    """
    assets = []
    parent_assets = []

    sync_queue = []

    if entity_type == "Task":
        assets = app.shotgun.find("Asset", [["tasks.Task.id", "in", entity_ids]], ["sg_asset_parent", "image"])

    if entity_type == "Asset":
        assets = app.shotgun.find("Asset", [['id', "in", entity_ids]], ["project.Project.code", "sg_asset_parent",
                         "code", "image",  'sg_asset_library', 'sg_asset_type', 'sg_asset_category'])

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
            try:
                fields = ctx.as_template_fields(asset_root_templ)
            except Exception as int_e:
                app.log_warning("Could not resolve from context: Using explicit fields instead.")
                fields = {}
                fields['Project'] = pa.get('project.Project.code')
                fields['asset_library'] = pa.get('sg_asset_library').get('name')
                fields['asset_type'] = pa.get('sg_asset_type')
                fields['asset_category'] = pa.get('sg_asset_category')
                fields['Asset'] = pa.get("code")


            # constructing an item to pass info in case context resolution is not possible 
            # (therefore P4 syncing would also not possible)

            item = { "asset" : pa }
            item['context'] = ctx.to_dict()
            #template = app.sgtk.templates.get()

            try:
                asset_root_path = asset_root_templ.apply_fields(fields, platform=sys.platform) 
                client_asset_root_path = os.path.join(asset_root_path, "...")

                item['root_path'] = client_asset_root_path
                
            except Exception as e:
                # store exception so it's readily visible to users
                item['error'] = e
                app.log_info(e)
            
            sync_queue.append(item)
    try:
        p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
        p4_fw.sync.sync_with_dialog(sync_queue)
    except:
        app.log_exception("Failed to Open Sync dialog!")
        return
