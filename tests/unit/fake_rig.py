"""A fake connection for the Usage tutorials' examples, whose instruments are real
drivers at real addresses: it records what is written, keeps it for the queries
that read it back, and answers the rest from a table. Nothing here models a
cryostat, so the tests check what the code sends and reads, not how a system
behaves."""

from pyacquisition.core import instrument as instrument_module

LOCKIN = "GPIB0::8::INSTR"
LAKESHORE = "GPIB0::12::INSTR"


class FakeConnection:
    """Stands in for an instrument at an address."""

    def __init__(self, address, replies):
        self.resource_name = address
        self.written = []
        self.replies = dict(replies)

    def write(self, message):
        self.written.append(message)
        header, _, arguments = message.partition(" ")
        first, _, rest = arguments.partition(",")
        self.replies[f"{header}? {first}" if rest else f"{header}?"] = rest or first
        return len(message)

    def query(self, message):
        reply = self.replies.get(message, "0")
        return reply(message) if callable(reply) else reply

    def close(self):
        pass


def open_fakes(monkeypatch, replies: dict[str, dict]) -> dict[str, FakeConnection]:
    """Opens a fake connection in place of each address, answering from its table
    in `replies`. Returns them by address, as they are opened."""
    opened = {}

    def open_resource(address, adapter="pyvisa", **options):
        opened[address] = FakeConnection(address, replies.get(address, {}))
        return opened[address]

    monkeypatch.setattr(instrument_module, "open_resource", open_resource)
    return opened


# A few plausible replies from the tutorials' lock-in and Lakeshore.
REPLIES = {
    LOCKIN: {"OUTP? 1": "1.2e-04", "OUTP? 2": "3.0e-06"},
    LAKESHORE: {"KRDG? A": "20.0", "SETP? 1": "20.0", "OUTMODE? 1": "1,1,0"},
}
