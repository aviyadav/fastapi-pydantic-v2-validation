from datetime import datetime
from typing import List
from uuid import UUID, uuid4


# --- Pydantic V2 ---
from pydantic import BaseModel, Field
class PydanticAddress(BaseModel):
    street: str
    city: str
    country: str
    postal_code: str
class PydanticUser(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    age: int
    is_active: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)
    address: PydanticAddress
    tags: List[str]


# --- msgspec ---
import msgspec
class MsgspecAddress(msgspec.Struct):
    street: str
    city: str
    country: str
    postal_code: str
class MsgspecUser(msgspec.Struct):
    id: UUID
    name: str
    email: str
    age: int
    is_active: bool
    created_at: datetime
    address: MsgspecAddress
    tags: List[str]
