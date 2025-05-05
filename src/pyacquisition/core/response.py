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
