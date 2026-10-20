# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .software import Clock, Calculator, RandomNumberGenerator, SignalGenerator, TextFile, TraceGenerator
from .software import PIDController as PIDController  # made in code, for a PID task: not in instrument_map
from .stanford_research import SR_830, SR_860
from .keithley import Keithley_2000, Keithley_6221
from .lakeshore import Lakeshore_340, Lakeshore_350
from .oxford_instruments import Mercury_IPS


instrument_map = {
    "Calculator": Calculator,
    "Clock": Clock,
    "RandomNumberGenerator": RandomNumberGenerator,
    "SignalGenerator": SignalGenerator,
    "TextFile": TextFile,
    "TraceGenerator": TraceGenerator,
    "Keithley_2000": Keithley_2000,
    "Keithley_6221": Keithley_6221,
    "SR_830": SR_830,
    "SR_860": SR_860,
    "Lakeshore_340": Lakeshore_340,
    "Lakeshore_350": Lakeshore_350,
    "Mercury_IPS": Mercury_IPS,
}
