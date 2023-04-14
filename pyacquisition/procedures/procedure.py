from PySide6 import QtWidgets, QtGui, QtCore
from functools import partial
import time


class PollingWorker(QtCore.QObject):
	

	_finished = QtCore.Signal()
	loop_time = QtCore.Signal(float)
	run_time = QtCore.Signal(float)


	def __init__(
			self, 
			poll_function, 
			test_function, 
			period = 1000,
			single_shot = False,
			*args, 
			**kwargs
			):
		super().__init__(*args, **kwargs)

		self._poll_function = poll_function
		self._test_function = test_function

		self._timer  = QtCore.QTimer(self)
		self._timer.timeout.connect(self.poll)
		self._period = period
		self._init_time = time.time()
		self._run_time = None
		self._loop_time = None


	def start_polling(self):
		self._timer.start(self._period) 
		self._run_time = time.time()
		self._loop_time = time.time()


	def stop_polling(self):
		self._timer.stop()


	def toggle_polling(self):
		if self._timer.isActive():
			self.stop_polling()
		else:
			self.start_polling()


	def finish_polling(self):
		self._timer.stop()
		self._finished.emit()


	def poll(self):
		self.task()
		t1 = time.time()
		self.loop_time.emit(t1 - self._loop_time)
		self.run_time.emit(t1 - self._run_time)
		self._loop_time = t1


	def task(self):
		v = self._poll_function()
		x = self._test_function()
		if x:
			self.finish_polling()



class Procedure(QtCore.QObject):


	_signal_start_worker = QtCore.Signal()
	_signal_stop_worker = QtCore.Signal()
	_signal_toggle_worker = QtCore.Signal()
	_signal_finish_worker = QtCore.Signal()

	_finished = QtCore.Signal()

	
	def __init__(
			self, 
			poll_function,
			period = 1000,
			single_shot = False,
			):
		super().__init__()

		self._poll_function = poll_function
		self._value_function = None
		self._test_function = None

		self._period = period
		self._single_shot = single_shot

		self._thread = QtCore.QThread()
		self._worker = None
		self._running = False

		self.finished = False


	@classmethod
	def poll(cls, poll_function, *args, **kwargs):
		""" 
		Take a callable that returns either True or False.
		Return a Procedure with a PollingWorker that will call
		func() until it returns True and will return a Finished
		signal.
		"""
		procedure = cls(poll_function, *args, **kwargs)
		return procedure


	@classmethod
	def listen(cls, signal):
		"""
		Take a signal. Return a Procedure with a worker that
		checks the result of the signal whenever it is emitted.
		"""
		pass


	def until(self, value_function):
		self._value_function = value_function
		return self


	def greater_than(self, value):
		self._test_function = lambda: self._value_function() > value
		return self


	def less_than(self, value):
		self._test_function = lambda: self._value_function() < value
		return self


	def equal_to(self, value):
		self._test_function = lambda: self._value_function() == value
		return self


	def start(self):
		self._init_worker()
		self._start_worker()


	def _init_worker(self):
		self._worker = PollingWorker(
			self._poll_function, 
			self._test_function, 
			period=self._period,
			)
		self._worker.moveToThread(self._thread)

		# Procedure signals -> worker slots
		self._signal_start_worker.connect(self._worker.start_polling)
		self._signal_stop_worker.connect(self._worker.stop_polling)
		self._signal_toggle_worker.connect(self._worker.toggle_polling)
		self._signal_finish_worker.connect(self._worker.finish_polling)
		# Worker signals -> procedure slots
		self._worker._finished.connect(self._finish)
		self._worker._finished.connect(self._cleanup_worker)

		self._thread.start()


	def _start_worker(self):
		self._signal_start_worker.emit()


	def _stop_worker(self):
		self._signal_stop_worker.emit()


	def _toggle_worker(self):
		self._signal_toggle_worker.emit()


	def _finish_worker(self):
		self._signal_finish_worker.emit()


	def _cleanup_worker(self):
		self._thread.quit()
		self._thread.wait()


	def _finish(self):
		print('Procedure Finished')
		self._finished.emit()
		self.finished = True



class ProcedureGroup(QtCore.QObject):
	""" A group of procedures that run concurrently.
	Finished is emitted once all procedures have completed.
	"""

	_finished = QtCore.Signal()


	def __init__(self):
		super().__init__()
		self._procedures = []
		self._n_complete = 0

		self.finished = False


	def add_procedure(self, procedure):
		self._procedures.append(procedure)


	def start(self):
		for procedure in self._procedures:
			procedure._finished.connect(self._increase_complete)
			procedure._finished.connect(self._check_complete)
			procedure.start()


	def _increase_complete(self):
		self._n_complete += 1


	def _check_complete(self):
		if self._n_complete == len(self._procedures):
			self._finish()


	def _finish(self):
		self._finished.emit()
		self.finished = True




class ProcedureList(QtCore.QObject):
	""" A list of procedures that run is series. When one
	finished, the next is started. Finished is emitted once
	the list has been emptied (completed). Elements in list
	can be Procedures, ProcedureGroups or ProcedureLists
	"""

	_signal_procedure_finished = QtCore.Signal()
	_finished = QtCore.Signal()


	def __init__(self):
		super().__init__()
		self._procedures = []

		self.finished = False


	def start(self):
		self._connect_next_procedure()
		self._start_next_procedure()


	def add_procedure(self, procedure):
		self._procedures.append(procedure)


	def add_procedures(self, *args):
		for arg in args:
			self.add_procedure(arg)


	def _remove_first_procedure(self):
		self._procedures = self._procedures[1:]


	def _connect_next_procedure(self):
		self._procedures[0]._finished.connect(self._procedure_finished)


	def _start_next_procedure(self):
		self._procedures[0].start()


	def _procedure_finished(self):
		self._remove_first_procedure()
		if len(self._procedures) != 0:
			print('STARTING NEXT PROCEDURE')
			self._connect_next_procedure()
			self._start_next_procedure()
		else:
			self._finish()


	def _finish(self):
		self._finished.emit()
		self.finished = True




