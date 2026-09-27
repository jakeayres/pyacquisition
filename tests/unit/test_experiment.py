from pyacquisition import Experiment


def test_experiment_initialization(tmp_path):
    """
    Test that an Experiment object can be initialized without errors.
    """
    experiment = Experiment(root_path=str(tmp_path))
    assert isinstance(experiment, Experiment)
