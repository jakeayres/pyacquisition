from pyvisa import ResourceManager


def pyvisa_adapter():
    rm = ResourceManager()
    print(rm.list_resources())
    return rm