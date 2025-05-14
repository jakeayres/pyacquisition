from ..instruments.oxford_instruments.mercury_ips import (
    ActivityStatus,
    SystemStatusM,
    ModeStatusN,
)

from ..core.logging import logger
from ..core import Task


import asyncio
from dataclasses import dataclass


@dataclass
class SweepMagneticField(Task):
    """Sweep magnetic field to setpoint"""

    magnet_psu: str
    setpoint: float
    ramp_rate: float
    new_chapter: bool = False

    def description(self):
        return f"Sweeping field to {self.setpoint} T at {self.ramp_rate} T/min"

    async def check_system_normal(self, magnet_psu):
        system_status = None
        wait_time = 1.0

        try:
            system_status = magnet_psu.get_system_status()
            await asyncio.sleep(wait_time)
            logger.info(f"Checking magnet system status: {system_status.name}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Magnet system status was not retrieved")
            print(e)
            raise e

        if system_status != SystemStatusM.NORMAL:
            raise ValueError(
                f"Magnet system status {system_status}. Expected {SystemStatusM.NORMAL}"
            )

    async def hold(self, magnet_psu):
        wait_time = 1.0

        try:
            logger.info('Setting magnet to "hold"')
            magnet_psu.hold()
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error('Error setting magnet to "hold"')
            print(e)
            raise e

    async def check_is_holding(self, magnet_psu):
        wait_time = 1.0

        try:
            activity_status = magnet_psu.get_activity_status()
            await asyncio.sleep(wait_time)
            logger.info(f"Checking magnet activity status: {activity_status.name}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Magnet activity status was not retrieved")
            print(e)
            raise e

        if activity_status != ActivityStatus.HOLD:
            raise ValueError(
                f"Magnet activity status {activity_status}. Expected {ActivityStatus.HOLD}"
            )

    async def check_is_to_setpoint(self, magnet_psu):
        wait_time = 1.0

        try:
            activity_status = magnet_psu.get_activity_status()
            await asyncio.sleep(wait_time)
            logger.info(f"Checking magnet activity status: {activity_status.name}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Magnet activity status was not retrieved")
            print(e)
            raise e

        if activity_status != ActivityStatus.TO_SETPOINT:
            raise ValueError(
                f"Magnet activity status {activity_status}. Expected {ActivityStatus.TO_SETPOINT}"
            )

    async def check_is_to_zero(self, magnet_psu):
        wait_time = 1.0

        try:
            activity_status = magnet_psu.get_activity_status()
            await asyncio.sleep(wait_time)
            logger.info(f"Checking magnet activity status: {activity_status.name}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Magnet activity status was not retrieved")
            print(e)
            raise e

        if activity_status != ActivityStatus.TO_ZERO:
            raise ValueError(
                f"Magnet activity status {activity_status}. Expected {ActivityStatus.TO_ZERO}"
            )

    async def set_ramp_rate(self, magnet_psu, ramp_rate):
        wait_time = 1.0

        # Set ramp rate
        try:
            magnet_psu.set_field_sweep_rate(self.ramp_rate)
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Error setting ramp rate")
            raise e

        # Check ramp rate is set to desired value
        try:
            rate = magnet_psu.get_field_sweep_rate()
            await asyncio.sleep(wait_time)
            logger.info(f"Ramp rate set to {ramp_rate} T/min OK")
        except Exception as e:
            logger.error("Error getting ramp rate")
            raise e

        if rate != self.ramp_rate:
            raise ValueError(
                f"Retrieved ramp rate not equal to set value. Set: {self.ramp_rate}. Got: {rate}"
            )

    async def set_setpoint(self, magnet_psu, setpoint):
        wait_time = 1.0

        try:
            magnet_psu.set_target_field(setpoint)
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error("Error setting target field")
            print(e)

        try:
            retrieved_setpoint = magnet_psu.get_setpoint_field()
            await asyncio.sleep(wait_time)
            logger.info(f"Setpoint set to {setpoint} T")
        except Exception as e:
            logger.error("Error setting field setpoint")
            raise e

        if retrieved_setpoint != setpoint:
            raise ValueError(
                f"Retrieved setpoint not equal to set value. Set: {setpoint}. Got: {retrieved_setpoint}"
            )

    async def switch_heater_on(self, magnet_psu):
        wait_time = 1.0

        try:
            logger.info("Switching switch heater on")
            magnet_psu.heater_on()
            await asyncio.sleep(15)
        except Exception as e:
            logger.error("magnet_psu.heater_on() failed")
            print(e)
            raise e

        try:
            magnet_psu.get_switch_heater_status()
            await asyncio.sleep(wait_time)
            logger.info("Switch heater switched on OK.")
        except Exception as e:
            logger.error("Switch heater status not retrieved")
            print(e)
            raise e

    async def switch_heater_off(self, magnet_psu):
        wait_time = 1.0

        try:
            logger.info("Switching switch heater off")
            magnet_psu.heater_off()
            await asyncio.sleep(15)
        except Exception as e:
            logger.error("magnet_psu.heater_off() failed")
            print(e)
            raise e

        try:
            magnet_psu.get_switch_heater_status()
            await asyncio.sleep(wait_time)
            logger.info("Switch heater switch off OK.")
        except Exception as e:
            logger.error("Switch heater status not retrieved")
            print(e)
            raise e

    async def sweep_to_setpoint(self, magnet_psu, setpoint):
        wait_time = 1.0

        try:
            await self.set_setpoint(setpoint)
            await asyncio.sleep(wait_time)
            magnet_psu.to_setpoint()
            await asyncio.sleep(wait_time)
            await self.check_is_to_setpoint()
            await asyncio.sleep(wait_time)
            logger.info(f"Sweeping field to {setpoint}")
            while magnet_psu.get_sweep_status() != ModeStatusN.REST:
                await asyncio.sleep(wait_time)
            logger.info(f"Reached setpoint field of {setpoint} T")
        except Exception as e:
            logger.error("Error sweeping up to setpoint field")
            raise e

    async def sweep_to_zero(self, magnet_psu):
        wait_time = 1.0

        try:
            magnet_psu.to_zero()
            await asyncio.sleep(wait_time)
            await self.check_is_to_zero()
            await asyncio.sleep(wait_time)
            logger.info("Sweeping field to 0 T")
            while magnet_psu.get_sweep_status() != ModeStatusN.REST:
                await asyncio.sleep(wait_time)
            logger.info("Reached zero field")
        except Exception as e:
            logger.error("Error sweeping down to zero field")
            raise e

    def log_magnet_status(self, magnet_psu):
        status = magnet_psu.get_activity_status()
        logger.info(f"Magnet status: {status.name}")

    async def run(self, experiment):
        magnet_psu = self.experiment.rack.instruments[self.magnet_psu]
        wait_time = 1.0

        await asyncio.sleep(wait_time)
        yield None

        try:
            # Set magnet to 'HOLD' (in case clamped)
            await self.hold(magnet_psu)
            yield None

            # Check system status
            await self.check_system_normal(magnet_psu)
            yield None

            # Check activity status
            await self.check_is_holding(magnet_psu)
            yield None

            # Turn on switch heater
            await self.switch_heater_on(magnet_psu)
            yield None

            experiment.scribe.next_file("Field Sweep to 0T", next_block=False)

            # Set ramp rate
            await self.set_ramp_rate(magnet_psu, self.ramp_rate)
            yield None

            # Go to setpoint
            await self.sweep_to_setpoint(magnet_psu, self.setpoint)
            yield None

            experiment.scribe.next_file("Field Sweep to 0T", next_block=False)

            # Go to zero
            await self.sweep_to_zero(magnet_psu)
            yield None

            # Turn off switch heater
            await self.switch_heater_off(magnet_psu)

        except Exception as e:
            logger.error("Error during field sweep")
            self.log_magnet_status(magnet_psu)
            print(e)
            raise e

        finally:
            # Raise exception if magnet status isn't normal (eg quenched, fault)
            await self.check_system_normal(magnet_psu)
            yield None
