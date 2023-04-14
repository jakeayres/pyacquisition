from .ui_record_widget import Ui_record_widget

from PySide6 import QtWidgets, QtGui, QtCore
import inspect, enum, time, json, os
from functools import partial

import numpy as np
import pandas as pd


class Worker(QtCore.QObject):

	loop_time = QtCore.Signal(float)
	run_time = QtCore.Signal(float)


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._timer = QtCore.QTimer(self)
		self._timer.timeout.connect(self.poll)
		self._rate = 1000

		self._data = {}
		self._path = None


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
		if self._data != {}:
			if os.path.exists(self._path):
				self._append_data()
			else:
				self._write_data()
			self._clear_data()

		t1 = time.time()
		self.loop_time.emit(t1-self._t0_loop)
		self.run_time.emit(t1-self._t0_time)
		self._t0_loop = time.time()


	def _clear_data(self):
		for k, v in self._data.items():
			self._data[k] = []


	def _write_data(self):
		df = pd.DataFrame(self._data)
		df.to_csv(
			self._path,
			mode='w',
			sep=',',
			index=False,
			header=True,
			)


	def _append_data(self):
		df = pd.DataFrame(self._data)
		df.to_csv(
			self._path,
			mode='a',
			sep=',',
			index=False,
			header=False,
			)


	def path_slot(self, path: str):
		self._path = path


	def data_slot(self, data: dict):

		if self._timer.isActive():

			for k, v in data.items():
				if k not in self._data:
					self._data[k] = [v]
				else:
					self._data[k].append(v)




class RecordWidget(QtWidgets.QWidget, Ui_record_widget):


	signal_start =  QtCore.Signal()
	signal_stop = QtCore.Signal()
	signal_toggle = QtCore.Signal()
	data_signal = QtCore.Signal(dict)
	path_signal = QtCore.Signal(str)


	def __init__(self):
		super().__init__()
		self.setupUi(self)

		self._callables = {}

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


	def _start_worker(self):

		self._worker = Worker()
		self._worker.moveToThread(self._thread)

		self.signal_stop.connect(self._worker.polling_stop)
		self.signal_start.connect(self._worker.polling_start)
		self.signal_toggle.connect(self._worker.polling_toggle)

		self.signal_toggle.connect(self._get_path)

		self.data_signal.connect(self._worker.data_slot)
		self.path_signal.connect(self._worker.path_slot)

		self._worker.loop_time.connect(self._update_loop_time)
		self._worker.run_time.connect(self._update_run_time)

		self._thread.start()


	def _stop_worker(self):
		self._thread.quit()
		self._worker.deleteLater()
		self._thread.deleteLater()


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
		self.points_label.setText(f'{t:.3f}')


	def _update_run_time(self, t: float):
		self.time_label.setText(f'{t:.3f}')


	def _get_path(self) -> str:
		root = self.directory_edit.text()
		stem = self.stem_edit.text()
		number = self.number_edit.text()
		return f'{root}/{stem}_{number}.data'


	def start(self):
		self.signal_start.emit()


	def stop(self):
		self.signal_stop.emit()


	def toggle(self):
		self.signal_toggle.emit()


	def set_directory(self, directory: str):
		self.directory_edit.setText(directory)
		self.path_signal.emit(self._get_path())


	def set_stem(self, stem: str):
		self.stem_edit.setText(stem)
		self.path_signal.emit(self._get_path())


	def set_number(self, number: int):
		self.number_edit.setText(f'{number:04}')
		self.path_signal.emit(self._get_path())


	def increment_file(self):
		i = int(self.number_edit.text())
		self.set_number(i+1)


	def receive_data(self, data: dict):
		self.data_signal.emit(data)


	def close_cleanly(self):
		self._stop_worker()
		self.deleteLater()

		