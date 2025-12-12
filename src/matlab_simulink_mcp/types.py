from typing import Optional
from pydantic import BaseModel


class Port(BaseModel):
    name: str
    index: int
    type: Optional[str] = None  # Simscape 일 경우 등


class Connection(BaseModel):
    From: str
    To: str


class Element(BaseModel):
    Name: str
    Type: str
    Source: Optional[str] = None

    Inports: Optional[list[Port]] = None
    Outports: Optional[list[Port]] = None
    SimscapePorts: Optional[list[Port]] = None


class SystemDescription(BaseModel):
    Elements: list[Element]
    Connections: list[Connection]
