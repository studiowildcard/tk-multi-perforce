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
General Perforce connection commands
"""

import os
import sgtk
from sgtk import TankError


class MultiPerforce(sgtk.platform.Application):

    def init_app(self):
        """
        Called as the app is being initialized
        """
        self.log_debug("%s: Initializing..." % self)

        # register commands:
        self.engine.register_command("Perforce Status...", self.show_connection_dlg)

        if not self.get_setting("desktop_app_only"):
            p = {
                "title": "Perforce: Sync Files",
                "supports_multiple_selection": True
            }
            self.engine.register_command("Perforce: Sync Files", self.sync_files, p)

        # (TODO) - these commands aren't quite finished yet!
        # self.engine.register_command("Check Out Scene...", self.check_out_scene)
        # self.engine.register_command("Revert Changes...", self.revert_scene_changes)
        # self.engine.register_command("Show Pending Publishes...", self.show_pending_publishes)

        # support connecting on startup:
        # Note, this runs every time the app is re-initialized (the engine is restarted).
        # however, the UI will only be shown when a connection can't be made with the
        # previous/cached settings so this should be infrequently!
        if self.engine.has_ui:
            connect_on_startup = self.get_setting("connect_on_startup")
            if connect_on_startup:
                self.log_debug("Attempting to connect to Perforce...")
                self.__connect_on_startup()

    def destroy_app(self):
        """
        Called when the app is being cleaned up
        """
        self.log_debug("%s: Destroying..." % self)

        self.log_debug("Destroying tk-multi-perforce")

    def show_connection_dlg(self):
        """
        Show the Perforce connection details dialog.
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.open_connection(self)

    def check_out_scene(self):
        """
        Check out the current scene from Perforce.
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.check_out_current_scene()

    def revert_scene_changes(self):
        """
        Discard any changes to the current scene and revert.
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.revert_scene_changes()

    def show_pending_publishes(self):
        """
        Show all publishes that are pending in Perforce.
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.show_pending_publishes()

    def sync_files(self, entity_type=None, entity_ids=None):
        """
        Show Perforce Sync Status Window
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.open_sync_files_dialog(self, entity_type, entity_ids)

    def __connect_on_startup(self):
        """
        Called when the engine starts to ensure that a connection to Perforce
        can be established.  Prompts the user for password/connection details
        if needed
        """
        tk_multi_perforce = self.import_module("tk_multi_perforce")
        tk_multi_perforce.connect(self)
