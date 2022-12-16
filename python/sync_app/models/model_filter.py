import sgtk
from sgtk.platform.qt import QtCore, QtGui
from ..utils.inspection import method_decorator, trace
import logging

logger = sgtk.platform.get_logger("model_filter.py")


#@method_decorator(trace)
class SortFilterModel(QtGui.QSortFilterProxyModel):
    """
    A proxy model that excludes files from the view
    that end with the given extension
    """

    def __init__(self, excludes, parent=None, *args, **kwargs):
        super(SortFilterModel, self).__init__(*args, **kwargs)
        self._excludes = excludes[:]
        self.main_ui = parent

    def filterAcceptsRow(self, srcRow, srcParent):
        """
        When asked if a given row is to be filtered or remain,
        use logic to decide and return true/false for the whole
        row.

        Args:
            srcRow (_type_): _description_
            srcParent (_type_): _description_

        Returns:
            bool: True if row is to remain, False if to be filtered
        """
   
   
        try:
            
            # get reference to main model parent and it's child (the main item we want info from)
            parent_item = self.sourceModel().item(srcParent)
            item = parent_item.child(srcRow)

            item.should_be_visible = True
            # TODO: take this logic from prototype phase and decouple our UI calls. 
            # Likely the way to go is to cache the filterable state into an object that represents 
            # the filters checked and UI elements relating to them
            # 
            # if item.schema is (certain schema:)
            #   if item.should_be_visible:
            

            # asserts that the level 1 children (asset items) will not be filtered away.
            if item.schema.schema_type == "asset_item":

                # check if the user has "hide if nothing to sync" checkbox
                if self.main_ui._hide_syncd.isChecked():
                    if not item.children:
                        item.should_be_visible = False
                                     
            else:
                filters = item.schema.extract_filters()
                for filter_name in filters: #we want to retrieve filter types enables
                    
                    # fetch index matching filter_name
                    column_index = item.schema.key_index_map.get(filter_name)
                    
                    # fetch data from the given column index
                    column = item.rowData[column_index]
                    
                    # grab users filter settings from disk
                    users_filter_preference_data = self.main_ui.utils.prefs.data.get("{}_filters".format(filter_name))
                    
                    # check if any data exist    
                    if users_filter_preference_data: 
                        
                        include_list = [k for k, v in users_filter_preference_data.items() if v is True] # list of filters that is enabled

                        # if there is no data for the given filter (step could be empty for instance)
                        if column:
                            
                            # is the data in the list of things to not filter 
                            if column not in include_list:
                                
                                # hide the data
                                item.should_be_visible = False
                                
                                # stop running through the include_list
                                break
                    
            return item.should_be_visible

        except Exception as e:
            self.main_ui.logger.error(self.main_ui.logger.exception("failed to execute FilterAcceptsRow"))
        return True