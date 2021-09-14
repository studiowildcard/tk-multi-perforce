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
import pprint
import sgtk
from utils import TemplateRootResolver

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
    Prepare asset root paths to search in p4 and show the Perforce sync dialog
    """
                    
    root_resolver = TemplateRootResolver(app, entity_type, entity_ids)
    entities_and_root_dirs = root_resolver.resolve()

    try:
        p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
        p4_fw.sync.sync_with_dialog(entities_and_root_dirs)
    except:
        app.log_exception("Failed to Open Sync dialog!")
        return

   