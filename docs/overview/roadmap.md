## Purpose of this document

This document outlines areas of development that core contributors are particularly interested in advancing within `pyacquisition`. Inclusion on this list does not guarantee implementation, as time and resources are limited. Instead, it signals that community contributions in these areas are encouraged and appreciated.

## Version 0.1.x

Version `0.1.x` is still undergoing basic development with much of the testing being performed in production. Whilst the API should mostly remain stable and backward compatible, we will only fully commit to maintaining backward compatibility at version `1.0.0`.

### Immediate Objectives

**Increase breadth of `Instrument` classes**. Instruments are mostly being added as and when they are required. Users are encouraged to implement their own classes. Once they are shown to be robust through software testing and "live" use, they are incorporated into the main code base.

**Increase the breadth of `Task` classes**. A number of core `Task` classes will be added shortly. These are mostly related to file I/O.

**Nested tasks**. A preliminary API for nesting tasks has been implemented and is being tested. That is, allowing tasks to call other tasks for sequential and parallel execution allowing for far more modular and maintainable code when tasks become complex. This will likely be included in the next update.

**More robust and complete unit testing**. Robust unit testing is somewhat limited. At the very least, the public API of each class should be **fully** unit tested.

**Integration testing**. Integration testing is severely lacking. This is a high priority objective. The public API should be **fully** integration tested to ensure changes are not breaking.

**A more complete documentation**. Guides, recipes decmonstrating more advanced usage will be added. The API reference could be better.

### General Architectural Goals

**Settle on a definitive public API**. Once the public API has been fully decided upon, `pyacqusition` will advance to version `1.0.0`. This will be the first version in which we will absolutely strive to maintain backwards compatibility between versions and minimize breaking changes.

**`pyacquisition.gui` submodule refactor**. The GUI is entirely beyond the concern of users of `pyacqusition` and is highly functional. For developers, the `gui` submodule leaves a lot to be desired.

**A `pyacquisition.beta` submodule** will be included for modules that are not garuanteed to maintain backwards compatibility in future versions. This will likely be added in version `1.0.0` given that everything is effectively in beta in verion `0.1.x`.


## Version 1.0.0

Version `1.0.0` is on the immediate horizon. Once the public API has been finalized, version `1.0.0` will be released.
