# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pydantic import BaseModel


class Response(BaseModel):
    status: int
    data: str


class NumericResponse(BaseModel):
    status: int
    data: float


class StringResponse(BaseModel):
    status: int
    data: str


class DictResponse(BaseModel):
    status: int
    data: dict
