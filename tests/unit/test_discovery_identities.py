"""The words each driver's reply to *IDN? contains (core/discovery.py), and
whether a reply has them (verify/spec.py). Discovery (roadmap 11) builds on
these; the setup page's Test uses them now."""

from pyacquisition.core import discovery
from pyacquisition.verify.spec import missing_words


def test_the_hardware_drivers_with_an_identity_are_listed():
    assert discovery.identities() == {
        "Keithley_2000": ("KEITHLEY", "MODEL 2000"),
        "Keithley_6221": ("KEITHLEY", "6221"),
        "SR_830": ("STANFORD", "SR830"),
        "SR_860": ("STANFORD", "SR860"),
        "Lakeshore_340": ("LSCI", "MODEL340"),
        "Lakeshore_350": ("LSCI", "MODEL350"),
    }


def test_a_spec_that_fails_to_load_is_left_out(monkeypatch):
    def broken(cls):
        if cls.__name__ == "SR_830":
            raise ValueError("broken")
        return real(cls)

    real = discovery.load_spec
    monkeypatch.setattr(discovery, "load_spec", broken)

    assert "SR_830" not in discovery.identities()
    assert "SR_860" in discovery.identities()


def test_a_reply_lacking_words_says_which_ignoring_case():
    assert missing_words(("STANFORD", "SR830"), "stanford_research_systems,SR830,1,1") == []
    assert missing_words(("STANFORD", "SR830"), "LSCI,MODEL350") == ["STANFORD", "SR830"]
    assert missing_words(("STANFORD", "SR830"), "Stanford,SR860") == ["SR830"]
