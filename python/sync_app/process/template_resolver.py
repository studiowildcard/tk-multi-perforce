import os
import sys
import sgtk
import traceback
from ..utils.inspection import method_decorator, trace


# @method_decorator(trace)
class TemplateResolver:
    def __init__(self, app=None, entity=None, p4=None):
        self.app = app

        self._entity = entity
        self._incoming_entity = entity
        if entity.get("type") in ["PublishedFile"]:
            self._entity = entity
        self.p4 = p4

    @property
    def root_template(self):
        mapping = {
            "CustomEntity01": "env_asset_root",
            "Asset": "asset_root",
            "Sequence": "sequence_root",
            "Shot": "shot_root",
        }
        entity_type = self.entity.get("type")
        if entity_type in mapping.keys():
            template_name = mapping.get(entity_type)
            return self.app.sgtk.templates.get(template_name)
        else:
            raise Exception(
                "No template specified for resolving root path for type: {}".format(
                    entity_type
                )
            )

    @property
    def template_fields(self):
        self.prepare_folders()
        fields = self.context.as_template_fields(self.root_template)
        return fields

    @property
    def entity(self):
        if not self._entity:
            if not self._incoming_entity.get("code"):
                self._entity = self.app.shotgun.find_one(
                    self._incoming_entity["type"],
                    [["id", "is", self._incoming_entity["id"]]],
                    ["code"],
                )
            else:
                self._entity = self._incoming_entity
        return self._entity

    @entity.setter
    def entity(self, entity):
        self._entity = entity

    @property
    def context(self):
        if self.entity:
            return self.app.sgtk.context_from_entity(
                self.entity["type"], self.entity["id"]
            )

    def prepare_folders(self):

        self.app.sgtk.create_filesystem_structure(
            self.entity["type"], self.entity["id"]
        )

    @property
    def root_path2(self):
        if self._incoming_entity.get("type") in ["PublishedFile"]:
            return self._incoming_entity.get("path_cache")
        else:
            # self.app.log_info(self.template_fields)
            templated_path = self.app.sgtk.paths_from_entity(self.entity["type"],self.entity["id"])
            if len(templated_path) == 1:
                return os.path.join(templated_path[0],"...")
            else:
                raise Exception(
                    f"Multiple root paths specified for resolving {self.entity}: {str(templated_path)}"
                )            

    @property
    def entity_info(self):
        try:
            info = {
                "entity": self.entity,
                "context": self.context,
                "root_path": self.root_path2,
            }   
        except Exception as e:
            info = {
                "error": e 
            }  
        return info
