from .ui_measure_widget import Ui_measure_widget
from ..type_widgets import FloatWidget, IntWidget, EnumWidget, ValueWidget, GraphicalFloatWidget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum, time, json
from functools import partial


import numpy as np


class Worker(QtCore.QObject):

	output = QtCore.Signal(dict)
	loop_time = QtCore.Signal(float)
	run_time = QtCore.Signal(float)


	def __init__(self, callables, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._callables = callables
		self._timer = QtCore.QTimer(self)
		self._timer.timeout.connect(self.poll)
		self._rate = 100


	def polling_start(self):
		self._timer.start(self._rate)
		self._t0_time = time.time()
		self._t0_loop = time.time()


	def polling_stop(self):
		self._timer.stop()


	def polling_toggle(self):
		poller_active = self._timer.isActive()
		if poller_active:
			self.polling_stop()
		else:
			self.polling_start()


	def poll(self):
		""" Continuous task
		"""
		self.output.emit({k: f() for k, f in self._callables.items()})
		t1 = time.time()
		self.loop_time.emit(t1-self._t0_loop)
		self.run_time.emit(t1-self._t0_time)
		self._t0_loop = time.time()



class MeasureWidget(QtWidgets.QWidget, Ui_measure_widget):


	signal_start =  QtCore.Signal()
	signal_stop = QtCore.Signal()
	signal_toggle = QtCore.Signal()

	data_signal = QtCore.Signal(dict)


	def __init__(self, rack):
		super().__init__()
		self.setupUi(self)

		self._rack = rack

		self._callables = {}
		#self._signals = {}
		self._widgets = {}

		self.run_button.clicked.connect(self.signal_toggle.emit)

		self.signal_toggle.connect(self._toggle_running)
		self.signal_toggle.connect(self._toggle_button)

		self.signal_stop.connect(self._set_running_false)
		self.signal_stop.connect(self._set_button_not_running)

		self.signal_start.connect(self._set_running_true)
		self.signal_start.connect(self._set_button_running)

		self._thread = QtCore.QThread()
		self._worker = None
		self._running = False

		self._start_worker()


	@classmethod
	def from_filepath(cls, filepath, rack):
		""" Create Rack object from filepath of json config
		"""
		with open(filepath) as f:
			return cls.from_file(f, rack)


	@classmethod
	def from_file(cls, file, rack):
		""" Create Rack object from json config file
		"""
		json_ = json.load(file)
		return cls.from_json(json_, rack)


	@classmethod
	def from_json(cls, json_, rack):
		""" Create Rack object from json config
		"""
		measure_widget = cls(rack)
		measure_widget._parse_dictionary(json_)
		return measure_widget


	def _parse_dictionary(self, json_):
		for inst, config in json_.items():
			if 'measure' in config:
				for name, measure_config in config['measure'].items():
					self.add_callable(name, self._rack.instruments[inst].queries[measure_config['method']])


	def _set_running_true(self):
		self._running = True


	def _set_running_false(self):
		self._running = False


	def _toggle_running(self):
		self._running = not self._running


	def _set_button_running(self):
		self.run_button.setText('Stop')
		self.run_button.setStyleSheet('\
			background: rgb(200, 50, 25);\
			border-radius: 5px;\
			color: white;'
		)


	def _set_button_not_running(self):
		self.run_button.setText('Run')
		self.run_button.setStyleSheet('\
			background: rgb(100, 200, 25);\
			border-radius: 5px;\
			color: white;'
		)


	def _toggle_button(self):
		if self._running:
			self._set_button_running()
		else:
			self._set_button_not_running()


	def _update_loop_time(self, t: float):
		self.loop_label.setText(f'{t:.3f}')


	def _update_run_time(self, t: float):
		self.time_label.setText(f'{t:.3f}')


	def _start_worker(self):

		self._worker = Worker(self._callables)
		self._worker.moveToThread(self._thread)
		#self._thread.started.connect(self._worker.polling_start)

		self.signal_stop.connect(self._worker.polling_stop)
		self.signal_start.connect(self._worker.polling_start)
		self.signal_toggle.connect(self._worker.polling_toggle)

		self._worker.output.connect(self._report_output)
		self._worker.loop_time.connect(self._update_loop_time)
		self._worker.run_time.connect(self._update_run_time)

		self._thread.start()


	def _stop_worker(self):
		self._thread.quit()
		self._worker.deleteLater()
		self._thread.deleteLater()


	def _widget_from_flat_type(self, type_):
		if type_ == int:
			return IntWidget
		elif type_ == float:
			return GraphicalFloatWidget
		elif issubclass(type_, enum.Enum):
			return EnumWidget
		else:
			return ValueWidget


	def _widget_from_callable(self, func):
		return_class = inspect.getfullargspec(func).annotations['return']
		widget = self._widget_from_flat_type(return_class)
		return widget


	def _report_output(self, response):
		for key, value in response.items():
			self._widgets[key].set_value(value)
		self.data_signal.emit(response)


	def start(self):
		self.signal_start.emit()


	def stop(self):
		self.signal_stop.emit()


	def toggle(self):
		self.signal_toggle.emit()


	def add_callable(self, key, func):
		""" Take a key and a callable function and add it to the dictionary
		of callables and add the appropriate widget to layout be displayed.
		"""
		self._callables[key] = func
		self._widgets[key] = self._widget_from_callable(func)(name=key)

		self.main_layout.addWidget(self._widgets[key], QtCore.Qt.AlignTop)


	def close_cleanly(self, ):
		self._stop_worker()
		self.deleteLater()