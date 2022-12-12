import os
import webbrowser
import json
import logging

logger = logging.getLogger(os.path.basename(__file__))



class PrefFile:
    def __init__(self, filename=".psdf"):
        
        self.root_dir = os.path.expanduser("~")
        self.pref_file = os.path.join(self.root_dir, filename)

        self.read()

    def write(self, data=None):
        if not data:
            data = self.data
        with open(self.pref_file, "w") as file_obj:
            json.dump(data, file_obj, indent=4)

    def read(self):
        if not os.path.isfile(self.pref_file):
            self.data = {}
            self.write(self.data)
        with open(self.pref_file, "r") as file_obj:
            self.data = json.load(file_obj)
            return self.data


def open_browser(path):
    """
    Open file in a local file browser using file path uri
    """
    webbrowser.open("file:///" + path)