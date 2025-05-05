from pyacquisition import Experiment


def test_experiment_initialization():
    """
    Test that an Experiment object can be initialized without errors.
    """
    experiment = Experiment()
    assert isinstance(experiment, Experiment)