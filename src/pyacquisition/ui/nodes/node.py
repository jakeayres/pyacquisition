import dearpygui.dearpygui as gui



class Canvas(object):

	def __init__(self):
		self._uuid = str(gui.generate_uuid())


	@classmethod
	def add_to_window(cls, window, label):
		canvas = cls()
		gui.add_node_editor(
			parent=window,
			label=label,
			tag=canvas._uuid,
		)
		return canvas



class Node(object):
	

	def __init__(self):
		self._uuid = str(gui.generate_uuid())
		self._inputs = {}
		self._output = {}


	@classmethod
	def add_to_canvas(cls, canvas, label):
		node = cls()
		gui.add_node(
			parent=canvas._uuid,
			label=label,
			tag=node._uuid,
		)
		return node


	def _input_uuid(self, label):
		return f'{self._uuid}_input_node_{label}'


	def _output_uuid(self, label):
		return f'{self._uuid}_output_node_{label}'


	def add_input(self, label):
		gui.add_node_attribute(
			parent=self._uuid,
			label=label,
			attribute_type=gui.mvNode_Attr_Input,
			tag=self._input_uuid(label)
		)


class NodeInput(object):


	def __init__(self):
		self._uuid = str(gui.generate_uuid())


	@classmethod
	def add_to_node(cls, node, label):
		node_attribute = cls()
		gui.add_node_attribute(
			parent=node._uuid,
			label=label,
			tag=node_attribute._uuid,
			attribute_type=gui.mvNode_Attr_Input,
		)
		return node_attribute



class NodeOutput(object):


	def __init__(self):
		self._uuid = str(gui.generate_uuid())


	@classmethod
	def add_to_node(cls, node, label):
		node_attribute = cls()
		gui.add_node_attribute(
			parent=node._uuid,
			label=label,
			tag=node_attribute._uuid,
			attribute_type=gui.mvNode_Attr_Output,
		)
		return node_attribute

