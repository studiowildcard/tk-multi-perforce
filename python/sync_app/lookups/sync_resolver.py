from ..schema.resolver import BaseResolver


class SyncResolver(BaseResolver):
    def __init__(self):

        # if you use a transformer method for heavy calculation,
        # you may intend to store

        super().__init__()

    def sync_item(self, dict_value):
        if dict_value and "depotFile" in dict_value:
            if dict_value.get("depotFile"):
                return dict_value.get("depotFile").split("/")[-1]

    def sync_status(self, dict_value):
        if self.row:
            if hasattr(self.row, "error"):
                if self.row.error:
                    self.row.tool_tip = self.row.error
                    return self.row.error
            if hasattr(self.row, "syncing"):
                if self.row.syncing:
                    return "Syncing..."
            if hasattr(self.row, "syncd"):
                if self.row.syncd:
                    return "Synced"
        return dict_value

    def asset_name(self, dict_value):
        count = 0
        if self.row:
            count = self.row.childCount()
        if count:
            return dict_value + " ({})".format(count)
        return dict_value

    def total_to_sync(self, dict_value):
        items = 0
        if dict_value != "Error":
            if self.row:
                items = self.row.childCount()
            filtered = items - self.row.visible_children()
            msg = "{} To Sync".format(items - filtered)

            if filtered:
                msg += " ({} filtered)".format(filtered)

            if not self.row.childItems:
                msg = "Up to date"
        else:
            msg = dict_value

        return msg

    def revision(self, dict_value):
        if hasattr(self.row, "newrev"):
            if self.row.syncd:
                have_revision = self.row.newrev
        else:
            have_revision = dict_value.get("haveRev", '0')        
        head_revision = dict_value.get("rev", "0")
        rev = "{}/{}".format(have_revision, head_revision)
        return rev

    def destination_path(self, dict_value):
        return dict_value.get("clientFile")
    
    def detail(self, dict_value):
        return dict_value.get("detail")    

    def file_size(self, dict_value):
        size = dict_value.get("fileSize")
        if size:
            return "{:.2f}".format(int(size) / 1024 / 1024)



