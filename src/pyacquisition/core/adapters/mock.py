def mock_adapter(data: dict) -> dict:
    """
    Mock adapter function that returns the input data unchanged.
    
    Args:
        data (dict): The input data to be processed.
    
    Returns:
        dict: The unchanged input data.
    """
    return MockAdapter()


class MockAdapter:
    """
    Mock adapter class that simulates the behavior of a real adapter.
    """
    
    pass


class MockResource:
    def __init__(
        self, 
        resource_name,
        read_termination='', 
        write_termination='',
        send_end=True,
        query_delay=0.0,
    ):
        self.resource_name = resource_name
        self.opened = True
        self._timeout = 2000  # Default timeout in ms
        self._read_termination = read_termination
        self._write_termination = write_termination
        self._send_end = send_end
        self._query_delay = query_delay

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        if value is None or value == float('+inf'):
            self._timeout = float('+inf')
        elif value < 1:
            self._timeout = 0  # Immediate
        else:
            self._timeout = value

    @timeout.deleter
    def timeout(self):
        self._timeout = float('+inf')
        
        
    @property
    def read_termination(self):
        return self._read_termination


    @read_termination.setter
    def read_termination(self, value):
        self._read_termination = value


    @property
    def write_termination(self):
        return self._write_termination


    @write_termination.setter
    def write_termination(self, value):
        self._write_termination = value
        
    
    @property
    def send_end(self):
        return self._send_end


    @send_end.setter
    def send_end(self, value):
        self._send_end = bool(value)


    @property
    def query_delay(self):
        return self._query_delay


    @query_delay.setter
    def query_delay(self, value):
        self._query_delay = float(value)


    def write(self, command):
        return f"Mock write to {self.resource_name}: {command}"


    def read(self):
        return f"Mock read from {self.resource_name}"


    def close(self):
        self.opened = False
        return f"Mock resource {self.resource_name} closed"


class MockResourceManager:
    def __init__(self):
        self.resources = {}

    def open_resource(self, resource_name):
        resource = MockResource(resource_name)
        self.resources[resource_name] = resource
        return resource

    def list_resources(self):
        # Return a list of mock resource names
        return tuple(self.resources.keys())

    def close(self):
        for resource in self.resources.values():
            resource.close()
        self.resources.clear()