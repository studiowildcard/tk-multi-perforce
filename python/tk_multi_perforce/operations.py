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
import pprint
import sys
import traceback

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
    Prepare assets to send to the P4 Sync window to process
    """
    try:
        specific_files = False
        entities_to_sync = []

        synclog = app.engine.sgtk.synchronize_filesystem_structure()
        app.log_debug(f"Synced Folders: {synclog}")
        
        if entity_type:
            # if a single task were selected, or launched from a task detail page
            if entity_type == "Task":
                tasks = app.shotgun.find(entity_type, [['id', 'in', entity_ids]], ['entity'])
                entities_to_sync = entities_from_tasks(app, tasks)

            # if assets were selected, make sure we have all the top level assets from child selections
            elif entity_type == "Asset":
                ids = []
                assets = app.shotgun.find(entity_type, [['id', 'in', entity_ids]], ['sg_asset_parent', 'code'])
                parent_asset_ids = ids.extend([i.get('sg_asset_parent').get('id') for i in assets if i.get('sg_asset_parent')])
                asset_ids = ids.extend([i.get('id') for i in assets if not i.get('sg_asset_parent')])    
                entities_to_sync = [{"type": entity_type, "id": id} for id in list(set(ids))]
                app.log_info(entities_to_sync)

            elif entity_type == "PublishedFile":
                specific_files = True
                pfiles = app.shotgun.find(entity_type, [['id', 'in', entity_ids]], ['entity', 'path_cache', 'path']) 
                entities_to_sync = pfiles
                app.log_info(entities_to_sync)

            elif entity_type == "Sequence":
                ids = []
                asset_ids = []
                seqs = app.shotgun.find("Sequence", [['id', 'in', entity_ids]], ["assets"])
                for seq in seqs:
                    asset_ids.extend([i.get('id') for i in seq.get('assets')])
                assets = app.shotgun.find('Asset', [['id', 'in', asset_ids]], ['sg_asset_parent', 'code'])
                parent_asset_ids = ids.extend([i.get('sg_asset_parent').get('id') for i in assets if i.get('sg_asset_parent')])
                asset_ids = ids.extend([i.get('id') for i in assets if not i.get('sg_asset_parent')])    
                entities_to_sync = [{"type": "Asset", "id": id} for id in list(set(ids))]

            # for other entity types, return the list of entity objects unmodified
            else:
                entities_to_sync = [{"type": entity_type, "id": id} for id in entity_ids]

            
        else: # if user launching without context
            # we look for all project tasks assigned to the current user
            user = app.context.user
            user_tasks = app.context.sgtk.shotgun.find("Task", 
                                                    [["task_assignees", "is", user],
                                                    ["project", "is", app.context.project],
                                                    ['sg_status_list', 'in', ['rdy', 'ip']]],
                                                    ["entity", "sg_status_list"])

            # look through all the possible entity links to these tasks, and keep all the unique ones to send to the UI
            user_assets = []
            entities_to_sync = entities_from_tasks(app, user_tasks)

    
        p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
        p4_fw.sync.sync_with_dialog(app, entities_to_sync, specific_files)
    except Exception:
        import traceback
        app.log_error("Failed to Open Sync dialog!")
        app.log_error(traceback.format_exc())
   

def entities_from_tasks(app, tasks):
    entities_to_sync = []
    uids = []
    if tasks:
        for task in tasks:
            linked_entity = task.get('entity')
            if linked_entity:
                uid = "{}_{}".format(linked_entity.get('type'), linked_entity.get('id'))

                if linked_entity.get('type') in ["Asset", "Sequence", "Shot", "CustomEntity01"]:
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
                    if (linked_entity.get('type') == "Asset"):
                        assets = app.shotgun.find(linked_entity.get('type'), [['id', 'in', [linked_entity.get('id')]]], ['sg_asset_parent'])

                    # Shot
                    elif (linked_entity.get('type') == "Shot"):
                        shot = app.shotgun.find_one("Shot", [['id', 'in', [linked_entity.get('id')]]], ['sg_sequence.Sequence.assets']) 
                        if shot.get('sg_sequence.Sequence.assets'):
                            asset_ids = [i.get('id') for i in shot.get('sg_sequence.Sequence.assets')]
                            assets = app.shotgun.find("Asset", [['id', 'in', asset_ids]], ['sg_asset_parent'])

                    # Sequence
                    elif (linked_entity.get('type') == "Sequence"):
                        seq = app.shotgun.find_one("Sequence", [['id', 'in', [linked_entity.get('id')]]], ['assets']) 
                        if seq.get('assets'):
                            assets = app.shotgun.find("Asset", [['id', 'in', [i.get('id') for i in seq.get('assets')]]], ['sg_asset_parent'])

                    # identify the parent asset if one exists
                    ids.extend([i.get('sg_asset_parent').get('id') for i in assets if i.get('sg_asset_parent')])
                    ids.extend([i.get('id') for i in assets if not i.get('sg_asset_parent')])   

                    # add all assets discovered if uid key not already in the dict. 
                    for id in list(set(ids)): 
                        uid = "{}_{}".format("Asset", id)
                        if uid not in uids:
                            uids.append(uid)                        
                            entities_to_sync.append({"type": "Asset", "id": id})      


    return entities_to_sync

   