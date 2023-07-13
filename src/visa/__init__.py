import pyvisa
from .prologix import PrologixResourceManager
from .dummy import DummyResourceManager


_backends = {
	'pyvisa': pyvisa.ResourceManager(),
	'prologix': PrologixResourceManager,
	'dummy': DummyResourceManager,
}


def resource_manager(backend='pyvisa', *args, **kwargs):
	return _backends[backend](*args, **kwargs)

