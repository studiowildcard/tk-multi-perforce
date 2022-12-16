class BaseResolver(object):

    """
    Description: This class acts as a base class for mandatory transformations of
    Schemas. Specific app Transformers live with the app itself and
    is subclassing BaseTransformers
    """

    def __init__(self):
        self._row = None

    @property
    def row(self):
        return self._row

    @row.setter
    def row(self, row):
        self._row = row

    def process_column(self, method_name, value):
        if hasattr(self, method_name):
            return getattr(self, method_name)(value)

    def resolve(self, row):
        # "Return transformed data"

        self._cached_data = []

        self.row = row

        schema = self.row.schema
        data = self.row.data_in

        for col in schema.schema:

            val = None
            # cerberus match against schema

            if data and data.get(col["key"]):
                val = data[col["key"]]
                if col.get("transform"):
                    val = self.process_column(col["transform"], val)

                    # self.transformers.col = self

            self._cached_data.append(val)
        return self._cached_data
