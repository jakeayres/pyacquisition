from ..core.logging import logger


class Response:
    """
    A class that represents a response in an OpenAPI schema.
    """

    def __init__(self, status_code: str, details: dict):
        self.status_code = status_code
        self.details = details

    @property
    def description(self) -> str:
        """
        Returns the description of the response.
        """
        return self.details.get("description", None)

    @property
    def schema(self) -> dict:
        """
        Returns the schema of the response.
        """
        return self.content.get("application/json", {}).get("schema", {})

    @schema.setter
    def schema(self, new_schema: dict):
        """
        Sets a new schema for the response.
        """
        if "application/json" not in self.details.get("content", {}):
            self.details.setdefault("content", {}).setdefault("application/json", {})
        self.details["content"]["application/json"]["schema"] = new_schema

    @property
    def content(self) -> dict:
        """
        Returns the schema of the response.
        """
        return self.details.get("content", {})


class MethodParameter:
    """
    A class that represents a parameter in an OpenAPI schema.
    """

    def __init__(self, name: str, details: dict):
        self.name = name
        self.details = details

    @property
    def required(self) -> bool:
        """
        Returns whether the parameter is required.
        """
        return self.details.get("required", False)

    @property
    def type_(self) -> str:
        """
        Returns the type of the parameter.
        """
        if "enum" in self.details.get("schema", {}):
            return "enum"
        return self.details.get("schema", {}).get("type", None)

    @property
    def title(self) -> str:
        """
        Returns the title of the parameter.
        """
        return self.details.get("schema", {}).get("title", None)

    @property
    def enum_values(self) -> list:
        """
        Returns the enum values of the parameter.
        """
        return self.details.get("schema", {}).get("enum", [])

    @property
    def schema(self) -> dict:
        """
        Returns the schema of the parameter.
        """
        return self.details.get("schema", {})

    @schema.setter
    def schema(self, new_schema: dict):
        """
        Sets a new schema for the parameter.
        """
        self.details["schema"] = new_schema

    @property
    def contains_reference(self) -> bool:
        """
        Returns whether the parameter contains a reference.
        """
        return "$ref" in self.details.get("schema", {})


class Method:
    def __init__(self, method: str, details: dict):
        self.method = method
        self.details = details

    @property
    def summary(self) -> str:
        """
        Returns the summary of the method.
        """
        return self.details.get("summary", None)

    @property
    def description(self) -> str:
        """
        Returns the description of the method.
        """
        return self.details.get("description", None)

    @property
    def parameters(self) -> list:
        """
        Returns the parameters of the method.
        """
        return {
            param["name"]: MethodParameter(param["name"], param)
            for param in self.details.get("parameters", [])
        }

    @property
    def responses(self) -> dict:
        """
        Returns the responses of the method.
        """
        responses = self.details.get("responses", {})
        return {
            status_code: Response(status_code, details)
            for status_code, details in responses.items()
        }

    def response(self, status_code: str) -> Response:
        """
        Returns the Response object for the specified status code.
        """
        return self.responses.get(status_code, None)


class Component:
    """
    A class that represents a component in an OpenAPI schema.
    """

    def __init__(self, name: str, details: dict):
        self.name = name
        self.details = details

    @property
    def title(self) -> str:
        """
        Returns the title of the component.
        """
        return self.details.get("title", None)

    @property
    def type(self) -> str:
        """
        Returns the type of the component.
        """
        return self.details.get("type", None)

    @property
    def attributes(self) -> dict:
        """
        Returns the attributes (properties) of the component.
        """
        properties = self.details.get("properties", {})
        return {
            name: ComponentAttribute(name, details)
            for name, details in properties.items()
        }

    def attribute(self, name: str) -> dict:
        """
        Returns the attribute (property in OpenAPI terminology) of the component by name.
        """
        return self.attributes.get(name, None)

    @property
    def required_attributes(self) -> list:
        """
        Returns the required attributes (properties) of the component.
        """
        return self.details.get("required", [])


class ComponentAttribute:
    """
    A class that represents a attribute (property) of a component in an OpenAPI schema.

    Attribute has been used instead of property to avoid confusion with the property decorator in Python.
    The term "property" in OpenAPI refers to the attributes of a schema object.
    """

    def __init__(self, name: str, details: dict):
        self.name = name
        self.details = details

    @property
    def type(self) -> str:
        """
        Returns the type of the property.
        """
        return self.details.get("type", None)

    @property
    def title(self) -> str:
        """
        Returns the title of the property.
        """
        return self.details.get("title", None)


class Path:
    """
    A class that represents a path in an OpenAPI schema.
    """

    def __init__(self, path: str, methods: dict):
        self.path = path
        self.methods = methods

    @property
    def get(self) -> dict:
        """
        Returns the GET method of the path.
        """
        return Method("get", self.methods.get("get", {}))

    @property
    def post(self) -> dict:
        """
        Returns the POST method of the path.
        """
        return Method("post", self.methods.get("post", {}))


class Schema:
    """
    A class that represents an OpenAPI schema.
    """

    def __init__(self, schema: dict):
        self.schema = schema

        try:
            self.resolve_parameter_references()
        except Exception as e:
            logger.error(f"Error resolving parameter references: {e}")

        try:
            self.resolve_response_references()
        except Exception as e:
            logger.error(f"Error resolving response references: {e}")

    def resolve_parameter_references(self):
        """
        Resolves references in the parameter schema.
        """
        for path in self.paths.values():
            for param in path.get.parameters.values():
                if param.contains_reference:
                    param.schema = self.component(
                        param.schema["$ref"].split("/")[-1]
                    ).details
                else:
                    logger.debug(f"Parameter {param.name} does not contain a reference")

    def resolve_response_references(self):
        """
        Resolves references in the responses schemas.
        """
        for path in self.paths.values():
            for response in path.get.responses.values():
                if "$ref" in response.schema:
                    logger.debug(f"Resolving reference: {response.schema['$ref']}")
                    response.schema = self.component(
                        response.schema["$ref"].split("/")[-1]
                    ).details

    @property
    def title(self) -> str:
        """
        Returns the title of the schema.
        """
        return self.schema.get("info", {}).get("title", None)

    @property
    def version(self) -> str:
        """
        Returns the version of the schema.
        """
        return self.schema.get("info", {}).get("version", None)

    @property
    def description(self) -> str:
        """
        Returns the description of the schema.
        """
        return self.schema.get("info", {}).get("description", None)

    @property
    def paths(self) -> dict[str, Path]:
        """
        Returns the paths of the schema as a dictionary of Path objects.
        """
        paths = self.schema.get("paths", {})
        return {path: Path(path, methods) for path, methods in paths.items()}

    def path(self, path: str) -> Path:
        """
        Returns the Path object for the specified path.
        """
        return self.paths.get(path, None)

    @property
    def components(self) -> dict[str, Component]:
        """
        Returns the components of the schema.
        """
        components = self.schema.get("components", {}).get("schemas", {})
        return {name: Component(name, details) for name, details in components.items()}

    def component(self, name: str) -> Component:
        """
        Returns the Component object for the specified name.
        """
        return self.components.get(name, None)
