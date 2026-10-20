# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .wait import WaitFor, WaitUntil
from .wait import WaitForValue as WaitForValue
from .wait import WaitForStable as WaitForStable
from .files import NewFile
from .measurements import PauseMeasurements, ResumeMeasurements, SetMeasurementPeriod
from .traces import AcquireTrace as AcquireTrace
from .ramp_temperature import RampTemperature as RampTemperature
from .field_sweep import RampMagnet as RampMagnet
from .field_sweep import RampMagnetToZero as RampMagnetToZero
from .field_sweep import SweepMagneticField as SweepMagneticField
from .pid import PID as PID
from .pid import PIDCalculation as PIDCalculation


standard_tasks = [
    NewFile,
    WaitFor,
    WaitUntil,
    PauseMeasurements,
    ResumeMeasurements,
    SetMeasurementPeriod,
]

# Registered by themselves when an instrument they are for is in the experiment.
# What a task is for is its `applies_to`.
instrument_tasks = [RampTemperature, SweepMagneticField]

# Registered once `setup()` has added the measurements, which their forms offer.
reading_tasks = [WaitForValue, WaitForStable]
