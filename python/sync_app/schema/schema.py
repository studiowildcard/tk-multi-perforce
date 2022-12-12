from re import template

import sys
import os
import logging
from tank_vendor import yaml


#TODO on schema class if creating empty class, this must specifically be specified

class Schemas(object):
    def __init__(self):
        self._schemas = {}

    def __contains__(self, name):
        if name in self._schemas.keys():
            return True
        return False



    def __getattr__(self, attr):
        attr = attr.replace(" ", "_").replace("-", "_")
        if attr not in self._schemas.keys():
            schema = Schema(template_schema=attr)

            self._schemas[attr] = schema
        return self._schemas[attr]


class Schema(object):
    def __init__(self, template_schema=None):

        self.schema = None
        self.type = None

        

        if template_schema != None:
            schema = self.load_schema_from_yaml(template_schema)
            self.schema = schema
            self.type = template_schema

            # get key name, column index mapping
            self.key_index_map = self.index_lookup()

    def index_lookup(self, key="key"):

        index_map = {}
        for idx, i in enumerate(self.schema):
            if key in i.keys():
                index_map[i[key]] = idx
        return index_map
    
    def extract_filters(self):
        filters = []
        for entry in self.schema:
            if entry.get('filter'):
                filters.append(entry.get('key'))
            
        return filters
                
 
    def load_schema_from_yaml(self, name_of_file):
        # TODO consider if the yaml file does not exist in the same folder.

        file_name = name_of_file + ".yml"
        dir_path = os.path.dirname(__file__)
        path = os.path.join(dir_path, file_name)

        try:
            with open(path) as f:
                schema = yaml.safe_load(f)

                # set the type attribute so we know which template we are using
                # self.type = list(schema.keys())[0]
                return schema

        except:
            #TODO lets implement a specific exception
            raise "TODO implement something here"

    @property
    def schema_type(self):
        return self.type


    @classmethod
    def from_name(cls, name):
        cls.load_schema_from_yaml(name)
        return cls

    @classmethod
    def set_schema_type(cls, type):

        """
        Description: change the schema type after class is created

        type: [str] type for the schema. For example Sync_item.
        """

        cls.type = type

    def validate_schema(self):
        # TODO: implement cerberus

        validation_keys = ["key", "title", "Name"]

        if self.schema.get("key") is None:
            raise KeyError("Schema not valid, value for key not found")
        else:
            print("validation passed")

    def create_schema(self, type=None, key=None, title=None, delegate=None):

        # self.type = type if type != None else "custom"

        schema = {"default": "No name"}

        schema["key"] = key
        schema["title"] = title
        schema["deletage"] = delegate

        # need to validate schema after creation. Should it happen here or should that be a specific call afterwards?
        self.schema = schema
        self.validate_schema()
