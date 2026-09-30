from keithley_2400 import Keithley_2400
from pyacquisition.verify import Entry, Hazard, Policy, verify

smu = Entry(
    name="smu",
    cls=Keithley_2400,
    adapter="pyvisa",
    resource="GPIB0::24::INSTR",
)

report = verify([smu], Policy(Hazard.REVERSIBLE))
print(report.text())
