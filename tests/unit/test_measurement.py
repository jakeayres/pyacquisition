from pyacquisition.core.measurement import Measurement


def test_mock_function(mocker):
    mock_function = mocker.Mock(side_effect=[42, 52, 62])
    result = mock_function()
    assert result == 42  # First call returns 42
    result = mock_function()
    assert result == 52  # Second call returns 52


def test_measurement_initialization(mocker):
    mock_function = mocker.Mock(side_effect=[42, 52, 62])
    measurement = Measurement(
        name="TestMeasurement", function=mock_function, call_every=2
    )

    assert measurement._name == "TestMeasurement"
    assert measurement._function == mock_function
    assert measurement._call_every == 2
    assert measurement._call_counter == 2
    assert measurement._result is None


def test_measurement_run_updates_result(mocker):
    mock_function = mocker.Mock(side_effect=[42, 52, 62])
    measurement = Measurement(
        name="TestMeasurement", function=mock_function, call_every=1
    )

    result = measurement.run()
    assert result == 42
    assert measurement._result == 42
    mock_function.assert_called_once()

    result = measurement.run()
    assert result == 52


def test_measurement_run_respects_call_every(mocker):
    mock_function = mocker.Mock(side_effect=[42, 52, 62])

    measurement = Measurement(
        name="TestMeasurement", function=mock_function, call_every=2
    )

    # First call should update the result
    result1 = measurement.run()
    assert result1 == 42
    mock_function.assert_called_once()

    # Second call should not update the result
    result2 = measurement.run()
    assert result2 == 42
    mock_function.assert_called_once()

    # Second call should not update the result
    result3 = measurement.run()
    assert result3 == 52
    # Second call should not update the result
    result3 = measurement.run()
    assert result3 == 52


def test_measurement_run_resets__call_counter(mocker):
    mock_function = mocker.Mock(return_value=42)
    measurement = Measurement(
        name="TestMeasurement", function=mock_function, call_every=2
    )

    measurement.run()  # First call
    measurement.run()  # Second call
    measurement.run()  # Third call, should reset the counter and call the function again

    assert mock_function.call_count == 2  # Function should be called twice


def test_measurement_run_handles_exceptions(mocker):
    mock_function = mocker.Mock(side_effect=Exception("Test exception"))
    measurement = Measurement(
        name="TestMeasurement", function=mock_function, call_every=1
    )

    result = measurement.run()

    assert result is None  # Result should remain None after exception
    assert measurement._call_counter == 1  # Call counter should reset
    mock_function.assert_called_once()
