# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from ..core import Task
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

    @property
    def description(self) -> str:
        return f"Starting new file: {self.file_name}. Increment block: {self.increment_block}"

    async def run(self, experiment):
        experiment._scribe.next_file(
            title=self.file_name, next_block=self.increment_block
        )
