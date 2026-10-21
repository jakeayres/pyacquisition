# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from ..core import Task
from ..core.scribe import title_problem
from dataclasses import dataclass


@dataclass
class NewFile(Task):
    """Start a new file

    Attributes:
        file_name (str): The name of the file to be created.
        increment_block (bool): Whether to increment the block number for the new file.
    """

    file_name: str
    increment_block: bool = False

    def __post_init__(self):
        super().__post_init__()
        # Refused as it is made, so that a task that starts files is refused before
        # anything is recorded into a file that can't be saved.
        problem = title_problem(self.file_name)
        if problem:
            raise ValueError(f"{problem.rstrip('.')}: {self.file_name!r}.")

    @property
    def description(self) -> str:
        return f"Starting new file: {self.file_name}. Increment block: {self.increment_block}"

    async def run(self, experiment):
        experiment._scribe.next_file(
            title=self.file_name, next_block=self.increment_block
        )
