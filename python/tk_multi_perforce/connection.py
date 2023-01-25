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
Handle connecting to Perforce and showing the connection dialog from the Shotgun
menu
"""

import sgtk
from sgtk import TankError

def connect(app):
    """
    Connect to Perforce.  If a connection can't be established with
    the current settings then the connection UI will be shown.
    """
    try:
        p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
        p4_fw.connection.connect()
    except TankError as e:
        app.log_exception("Failed to connect!")
        raise 


def open_connection(app):
    """
    Show the Perforce connection dialog
    """
    try:
        p4_fw = sgtk.platform.get_framework("tk-framework-perforce")
        p4_fw.connection.connect_with_dialog()
    except:
        app.log_exception("Failed to Open Connection dialog!")
        raise Exception("Failed to Open Connection dialog!")
    

      
        
        
        