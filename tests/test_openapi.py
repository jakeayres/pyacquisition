from pyacquisition.gui.openapi import Schema


def test_schema_initialization():
    schema_data = {"info": {"title": "Test API", "version": "1.0.0", "description": "Test description"}}
    schema = Schema(schema_data)
    assert schema.schema == schema_data


def test_schema_title():
    # Test when title is present
    schema_data = {"info": {"title": "Test API"}}
    schema = Schema(schema_data)
    assert schema.title == "Test API"

    # Test when title is missing
    schema_data = {"info": {}}
    schema = Schema(schema_data)
    assert schema.title is None

    # Test when info is missing
    schema_data = {}
    schema = Schema(schema_data)
    assert schema.title is None


def test_schema_version():
    # Test when version is present
    schema_data = {"info": {"version": "1.0.0"}}
    schema = Schema(schema_data)
    assert schema.version == "1.0.0"

    # Test when version is missing
    schema_data = {"info": {}}
    schema = Schema(schema_data)
    assert schema.version is None

    # Test when info is missing
    schema_data = {}
    schema = Schema(schema_data)
    assert schema.version is None


def test_schema_description():
    # Test when description is present
    schema_data = {"info": {"description": "Test description"}}
    schema = Schema(schema_data)
    assert schema.description == "Test description"

    # Test when description is missing
    schema_data = {"info": {}}
    schema = Schema(schema_data)
    assert schema.description is None

    # Test when info is missing
    schema_data = {}
    schema = Schema(schema_data)
    assert schema.description is None
    

def test_schema_paths():
    # Test when paths are present
    schema_data = {
        "paths": {
            "/test": {
                "get": {
                    "summary": "Test summary",
                    "description": "Test description",
                    "parameters": {"param1": "value1"}
                }
            }
        }
    }
    schema = Schema(schema_data)
    assert "/test" in schema.paths
    assert schema.path("/test").get.summary == "Test summary"
    assert schema.path("/test").get.description == "Test description"

    # Test when paths are missing
    schema_data = {}
    schema = Schema(schema_data)
    assert schema.paths == {}