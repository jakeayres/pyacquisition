"""
Utility functions to assist with the parsing of the 
OpenAPI schema (json file at localhost:port/openapi.json)
"""



class Schema:


	def __init__(self, schema):
		self._schema = schema


	@property
	def schema(self):
		return self._schema


	def path_display_name(self, path):
		return f'{self.path_tags(path)[0]}: {self.path_summary(path)}'


	def path_summary(self, path):
		return self._schema['paths'][path]['get']['summary']


	def path_description(self, path):
		return self._schema['paths'][path]['get']['description']


	def paths_with_tag(self, tag):
		return {k: v for k, v in self._schema['paths'].items() if tag in v['get']['tags']}


	def has_parameters(self, path):
		if 'parameters' in self._schema['paths'][path]['get']:
			return True
		else:
			return False


	def path_tags(self, path):
		return self._schema['paths'][path]['get']['tags']


	def endpoint_parameters(self, path):
		return self._schema['paths'][path]['get']['parameters']


	def endpoint_path_parameters(self, path):
		return [p for p in self.endpoint_parameters(path) if p['in']=='path']


	def endpoint_query_parameters(self, path):
		return [p for p in self.endpoint_parameters(path) if p['in']=='query']


	def resolve_component_ref(self, ref):
		parts = ref.split('/')[1:]
		schema = self._schema
		for p in parts:
			schema = schema[p]
		return schema


	def parameter_type(self, parameter):
		if '$ref' in parameter['schema']:
			return self.resolve_component_ref(parameter['schema']['$ref'])
		elif 'type' in parameter['schema']:
			return parameter['schema']['type']
		else:
			# HANDLE THIS
			pass