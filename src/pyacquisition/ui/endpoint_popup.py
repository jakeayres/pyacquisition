import dearpygui.dearpygui as gui
import requests
import json


class EndpointPopup:


	_window_uuid_suffix = '_window'
	_response_input_uuid_suffix = '_response'


	def __init__(
		self, 
		path, 
		schema,
		pos=[150, 150],
		):

		self._uuid = str(gui.generate_uuid())
		self._path = path
		self._path_params = self._make_path_parameter_dictionary(schema, path)
		self._query_params = self._make_query_parameter_dictionary(schema, path)

		with gui.window(
			tag=self.window_uuid,
			label=schema.path_display_name(path), 
			width=300,
			pos=pos,
			):
			gui.add_text(path, color=(100,100,100))

			if schema.has_parameters(path):
				for param in schema.endpoint_parameters(path):
					param_type = schema.parameter_type(param)
					if isinstance(param_type, dict):
						self._add_enum_input(param, param_type)
					elif param_type == 'string':
						self._add_text_input(param)
					elif param_type == 'boolean':
						self._add_boolean_input(param)
					else:
						self._add_text_input(param)

			gui.add_button(label='Execute', callback=self.request, width=150)

			gui.add_input_text(hint='response', tag=self.response_uuid, width=280)


	@classmethod
	def from_config(cls, config, schema):
		return cls(
			config['path'],
			schema,
			config['pos'],
			)


	def config(self):
		data = {
			'path': self._path,
			'pos': gui.get_item_pos(self.window_uuid),
		}
		return data


	@property
	def window_uuid(self):
		return self._uuid + self._window_uuid_suffix
	

	@property
	def response_uuid(self):
		return self._uuid + self._response_input_uuid_suffix



	def _make_parameter_uuid(self, param_name):
		return '_'.join([self._uuid, param_name, 'uuid'])


	def _make_path_parameter_dictionary(self, schema, path):
		if schema.has_parameters(path):
			return {param['name']:'' for param in schema.endpoint_path_parameters(path)}
		else:
			return {}


	def _make_query_parameter_dictionary(self, schema, path):
		if schema.has_parameters(path):
			return {param['name']:'' for param in schema.endpoint_query_parameters(path)}
		else:
			return {}


	def _get_callback(self, param):
		if param['in'] == 'path':
			return self._set_path_parameter
		elif param['in'] == 'query':
			return self._set_query_parameter


	def _set_path_parameter(self, sender, app_data, user_data):
		self._path_params[user_data['key']] = gui.get_value(user_data['uuid'])


	def _set_enum_parameter(self, sender, app_data, user_data):
		self._path_params[user_data['key']] = gui.get_value(user_data['uuid'])


	def _set_query_parameter(self, sender, app_data, user_data):
		self._query_params[user_data['key']] = gui.get_value(user_data['uuid'])


	def _add_text_input(self, param):
		_id = self._make_parameter_uuid(param['name'])
		gui.add_input_text(
			tag=_id,
			label=f"{param['name']:>14}",
			callback=self._get_callback(param), 
			user_data={'key': param['name'], 'uuid': _id},
			width=150,
			)


	def _add_boolean_input(self, param):
		_id = self._make_parameter_uuid(param['name'])
		gui.add_checkbox(
			tag=_id,
			label=f"{param['name']:>14}",
			callback=self._get_callback(param),
			user_data={'key': param['name'], 'uuid': _id},
			indent=130,
			)


	def _add_enum_input(self, param, param_type):
		_id = self._make_parameter_uuid(param['name'])
		gui.add_combo(
			tag=_id,
			label=f"{param['name']:>14}",
			items=param_type['enum'],
			callback=self._set_enum_parameter,
			user_data={'key': param['name'], 'uuid': _id},
			width=150,
			)


	def _make_endpoint(self):
		endpoint = self._path

		for k, v in self._path_params.items():
			endpoint = endpoint.replace('{'+k+'}', str(v))

		query_string = '&'.join([f'{k}={v}' for k, v in self._query_params.items()])
		
		if query_string != '':
			endpoint = endpoint + '?' + query_string

		return endpoint


	def request(self):
		endpoint = 'http://localhost:8000'+self._make_endpoint()
		value = requests.get(endpoint, timeout=1)
		value = json.loads(value.content.decode('utf-8'))
		gui.set_value(self._uuid+'response_input', json.dumps(value))
		return value
