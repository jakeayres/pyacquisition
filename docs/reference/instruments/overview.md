Every instrument driver that comes with PyAcquisition. [Connect a real instrument](../../usage/connect_instrument.md) shows them in use, and [Write a hardware instrument](../../usage/hardware_instrument.md) shows how to write another.

The name on each card is the driver's: the class to import from `pyacquisition.instruments`, and what a config file's `instrument` takes. A **hardware** instrument takes a name and an address, and a **software** instrument only a name. Each page lists the driver's queries and commands, from its code.

<div class="pa-makers" markdown>

<div class="pa-maker" markdown>

## Keithley

-   [**Keithley_2000**](keithley_2000.md)  
    6½-digit digital multimeter.
-   [**Keithley_6221**](keithley_6221.md)  
    AC and DC current source.

</div>

<div class="pa-maker" markdown>

## Lakeshore

-   [**Lakeshore_340**](lakeshore_340.md)  
    Temperature controller.
-   [**Lakeshore_350**](lakeshore_350.md)  
    Cryogenic temperature controller.

</div>

<div class="pa-maker" markdown>

## Oxford Instruments

-   [**Mercury_IPS**](mercury_ips.md)  
    Superconducting magnet power supply.

</div>

<div class="pa-maker" markdown>

## Stanford Research Systems

-   [**SR_830**](sr_830.md)  
    DSP lock-in amplifier.
-   [**SR_860**](sr_860.md)  
    500 kHz DSP lock-in amplifier.

</div>

<div class="pa-maker pa-maker--wide" markdown>

## Software instruments

-   [**Calculator**](calculator.md)  
    Arithmetic and trigonometry, for trying queries and commands.
-   [**Clock**](clock.md)  
    Software clock.
-   [**PIDController**](pid_controller.md)  
    The controls of a running `PID` task, in the interface. Made in code, given the PID, so not in a config file.
-   [**RandomNumberGenerator**](random_number_generator.md)  
    Random numbers from common probability distributions.
-   [**SignalGenerator**](signal_generator.md)  
    Software waveform generator.
-   [**TraceGenerator**](trace_generator.md)  
    Simulated spectrum, to try traces without hardware.

</div>

</div>
