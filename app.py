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
import sys
from sgtk import TankError
import traceback


class MultiPerforce(sgtk.platform.Application):
    def init_app(self):
        """
        Called as the app is being initialized
        """
        self.log_debug("%s: Initializing..." % self)

        # register commands:
        self.engine.register_command("Perforce Status...", self.show_connection_dlg)

        if not self.get_setting("desktop_app_only"):
            p = {"title": "Perforce: Sync Files", "supports_multiple_selection": True}
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

        # now register a *command*, which is normally a menu entry of some kind on a Shotgun
        # menu (but it depends on the engine). The engine will manage this command and
        # whenever the user requests the command, it will call out to the callback.

    def handle_connection_error(self, force_banner=None):
        """
        Show banner notifying user of Perforce connection issue.
        :param: force_banner: Utilize this when the UI is already fully loaded
            but you still need to trigger a banner update.
        """
        # trigger a visible banner in SG Desktop
        if self.engine.name in ["tk-desktop"]:

            log_location = sgtk.log.LogManager().log_folder.replace("\\", "/")
            self.banner_error_message = "<br><center><font color='red'><b>Warning!</b></font> Could not connect to Perforce server."\
                "<br>See <b>tk-desktop</b> <a href='file:///{}'>logs.</a> locating lines for [<i>{}</i>]<br>".format(log_location, self.name)
            force_banner = False
            if force_banner:
                #self.engine._project_comm.call_no_response("update_banners", self.banner_error_message)
                pass
            else:
                os.environ['SGTK_DESKTOP_PROJECT_BANNER_MESSAGE'] = self.banner_error_message

            banner_message = (
                "<br><center><font color='red'><b>Warning!</b></font> Could not connect to Perforce server."
                "<br>See <b>tk-desktop</b> <a href='file:///{}'>logs.</a> locating lines for [<i>{}</i>]<br>".format(
                    log_location, self.name
                )
            )
            force_banner = False
            if force_banner:
                # self.engine._project_comm.call_no_response(
                #    "update_banners", banner_message
                #)
                pass
            else:
                os.environ["SGTK_DESKTOP_PROJECT_BANNER_MESSAGE"] = banner_message

        self.log_error(
            "tk-multi-perforce is unable to load: {}".format(traceback.format_exc())
        )

    def handle_connection_success(self, force_banner=None):
        # trigger a visible banner in SG Desktop
        if self.engine.name in ['tk-desktop']:

            log_location = sgtk.log.LogManager().log_folder.replace("\\", "/")
            self.banner_success_message = "<br><center><font color='blue'><b>Success!</b></font> Connection to Perforce server is successful." \
                             "<br>See <b>tk-desktop</b> <a href='file:///{}'>logs.</a> locating lines for [<i>{}</i>]<br>".format(
                log_location, self.name)
            force_banner = False
            if force_banner:
                #self.engine._project_comm.call_no_response("update_banners", self.banner_success_message)
                pass
            else:
                os.environ['SGTK_DESKTOP_PROJECT_BANNER_MESSAGE'] = self.banner_success_message

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
        try:
            tk_multi_perforce = self.import_module("tk_multi_perforce")
            result = tk_multi_perforce.open_connection(self)
            if result:
                self.log_debug("Connection to Perforce server is successful!")
                self.handle_connection_success(force_banner=True)

        except:
            self.handle_connection_error(force_banner=True)

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

    def sync_files_original(self, entity_type=None, entity_ids=None):
        """
        Show Perforce Sync Status Window
        """
        try:
            self.log_debug("Importing tk_multi_perforce...")
            tk_multi_perforce = self.import_module("tk_multi_perforce")
            tk_multi_perforce.connect(self)
            # tk_multi_perforce.open_sync_files_dialog(self, entity_type, entity_ids)

            #app_payload = self.import_module("sync_app")
            #app_payload.dialog.open_sync_files_dialog(self, entity_type, entity_ids)

            try:
                # Dynamically set the module path for compatibility
                current_dir = os.path.dirname(os.path.abspath(__file__))
                python_dir = os.path.join(current_dir, 'python')

                if python_dir not in sys.path:
                    sys.path.append(python_dir)

                # Import sync_app.dialog after ensuring the path is set
                self.log_debug("Importing sync_app...")
                from sync_app import dialog
                dialog.open_sync_files_dialog(self, entity_type, entity_ids)

            except:
                self.handle_connection_error(force_banner=True)
        except:
            self.handle_connection_error(force_banner=True)

    def sync_files(self, entity_type=None, entity_ids=None):
        """
        Show Perforce Sync Status Window.
        """
        try:
            # Log the start of the method
            self.log_debug("Starting the sync_files process...")

            # Attempt to import the tk_multi_perforce module
            self.log_debug("Importing tk_multi_perforce module...")
            tk_multi_perforce = self.import_module("tk_multi_perforce")
            tk_multi_perforce.connect(self)
            self.log_debug("Successfully connected to Perforce through tk_multi_perforce.")

            # Ensure the correct path is set for sync_app imports
            current_dir = os.path.dirname(os.path.abspath(__file__))
            python_dir = os.path.join(current_dir, 'python')

            if python_dir not in sys.path:
                self.log_debug(f"Appending {python_dir} to sys.path...")
                sys.path.append(python_dir)

            # Import sync_app and handle the dialog
            self.log_debug("Importing sync_app.dialog module...")
            from sync_app import dialog
            dialog.open_sync_files_dialog(self, entity_type, entity_ids)
            self.log_debug("Successfully opened the sync dialog.")

        except TankError as e:
            # Log specific TankError exceptions
            self.log_error(f"Failed to import tk_multi_perforce module: {e}")
            self.handle_connection_error(force_banner=True)

        except ImportError as e:
            # Log any ImportError exceptions
            self.log_error(f"ImportError: {e}. Check if 'sync_app' is correctly located.")
            self.handle_connection_error(force_banner=True)

        except Exception as e:
            # Log any other unexpected errors with a detailed traceback
            self.log_error(f"Unexpected error occurred: {traceback.format_exc()}")
            self.handle_connection_error(force_banner=True)

        finally:
            # Log completion of the method, whether successful or not
            self.log_debug("sync_files method completed.")

    def __connect_on_startup(self):
        """
        Called when the engine starts to ensure that a connection to Perforce
        can be established.  Prompts the user for password/connection details
        if needed
        """
        try:
            tk_multi_perforce = self.import_module("tk_multi_perforce")
            tk_multi_perforce.connect(self)
        except:
            self.handle_connection_error()
