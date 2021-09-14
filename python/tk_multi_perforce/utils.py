import os
import sys

name_mapping = {
    "Animation": "CustomEntity05",
    "Env Asset": "CustomEntity01",
}

root_template_mapping = {
    "Asset" : "asset_root",
    "Animation" : "anim_asset_root",
    "Env Asset" : "env_asset_root"
}


class TemplateRootResolver:

    def __init__(self, app, entity_type, entity_ids):
        self.app = app
        self.entity_type = entity_type
        self.entity_ids = entity_ids

        self.type_mapping = {entity_type:name for name, entity_type in name_mapping.items()}
        self.entity_name = self.entity(entity_type, reverse=True)
        

    def entity(self, key, reverse=None):
        """
        Translates to/from custom entity type names
        """

        lookup_map = name_mapping
        if reverse:
            lookup_map = self.type_mapping
        if key in lookup_map.keys():
            return lookup_map[key]
        else:
            return key

    @property
    def root_template(self):
        """
        Get root template from explicit map
        returns: TemplatePath obj
        """
        if self.entity_name in root_template_mapping.keys():
            
            self._root_template = root_template_mapping[self.entity_name]
            template = self.app.sgtk.templates[self._root_template]
            return template
        else:
            raise Exception('No root template mapping found for {}s'.format(self.entity_name))


    def fields_from_template(self):
        template = self.root_template
        search_map = {}
        if template:
            for template_field_name, template_key in template.keys.items():
                entity_type = template_key.shotgun_entity_type
                if entity_type:
                    if not search_map.get(entity_type):
                        search_map[entity_type] = {}
                    
                    search_map[entity_type][template_key.shotgun_field_name] = template_field_name

            return search_map


    def resolve(self):

        # defaults
        filters = [["id", "in", self.entity_ids]]
        standard_fields = ['project.Project.code', 'code']


        items = []

        template_fields = {}

        for entity_type, template_field_map in self.fields_from_template().items():
            search_fields = template_field_map.keys()
            search_fields.extend(standard_fields)

            result = self.app.shotgun.find(entity_type, filters, search_fields)

            # result guaranteed since it's an API lookup from an explicit selection
            for entity in result:
                try:
                    item = {}
                    item['asset'] = entity
                    item['context'] = self.app.sgtk.context_from_entity(entity['type'],  entity['id'])

                    template_fields = {}
                    for field, template_field in template_field_map.items():
                        template_fields[template_field] = entity.get(field)

                        # assert metadata present in all entities but not explicit in the template
                        template_fields["Project"] = entity.get('project.Project.code')
                        template_fields[self.entity(entity.get('type'))] = entity.get('code')

                    template = self.root_template
                    path =  template.apply_fields(template_fields, platform=sys.platform)

                    item['root_path'] = os.path.join(path, "...")

                    self.app.log_info(path)
                except Exception as e:
                    item['error'] = str(e)

                items.append(item)

        return items