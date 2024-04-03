"""
Utility functions to assist with the parsing of the 
OpenAPI schema (json file at localhost:port/openapi.json)
"""



class Schema:


	def __init__(self, schema):
		self._schema = schema


	def paths_with_tag(self, tag):

		return {k: v for k, v in self._schema['paths'].items() if tag in v['get']['tags']}