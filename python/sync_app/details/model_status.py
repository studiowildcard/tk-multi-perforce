# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk


class SgStatusModel(sgtk.platform.qt.QtGui.QStandardItemModel):
    """
    This model represents status codes.
    """

    def __init__(self, parent, bg_task_manager):
        """
        Constructor
        """
        # Import the framework here to ensure it runs in the app context
        shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_model")
        ShotgunModel = shotgun_model.ShotgunModel

        # Call the superclass constructor
        super(SgStatusModel, self).__init__(parent)

        # Initialize ShotgunModel within the constructor
        self._shotgun_model = ShotgunModel(parent, download_thumbs=True, bg_task_manager=bg_task_manager)
        fields = ["bg_color", "icon", "code", "name"]
        self._shotgun_model._load_data("Status", [], ["code"], fields)
        self._shotgun_model._refresh_data()

    ############################################################################################
    # public methods

    def get_color_str(self, code):
        """
        Returns the color, as a string, for example '202,244,231'
        """
        for idx in range(self.rowCount()):
            item = self.item(idx)

            if item.text() == code:
                return item.get_sg_data().get("bg_color")

        return None

    def get_long_name(self, code):
        """
        Returns the long name for a status, 'Undefined' if not found.
        """
        for idx in range(self.rowCount()):
            item = self.item(idx)
            if item.text() == code and item.get_sg_data().get("name"):
                # avoid non-None values
                return item.get_sg_data().get("name")

        return "Undefined"
