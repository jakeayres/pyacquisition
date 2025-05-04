# Creating Custom Instruments

`pyacquisition` has implemented classes for a number of common instruments. The list is far from exhaustive. It is anticipated that you will need to write your own class that harnesses the functionality of your instrument. The process is simple. An outline of the workflow is as follows:

1. Compose your instrument inhereting from `Instrument` or `SoftwareInstrument`
2. Mark your methods with either `@mark_command` or `@mark_query`
3. Add the instrument in `your_experiment.setup()`


