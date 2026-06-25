import msgspec
from fastapi import FastAPI, Response
from pydantic import BaseModel

app = FastAPI()


# Input validation: Pydantic
class UserCreate(BaseModel):
    name: str
    email: str
    age: int


# Response model: Pydantic (FastAPI-compatible)
class UserResponse(msgspec.Struct):
    id: str
    name: str
    email: str
    age: int


@app.post("/users", response_model=None)
async def create_user(data: UserCreate):
    user = UserResponse(id="123", name=data.name, email=data.email, age=data.age)
    return Response(content=msgspec.json.encode(user), media_type="application/json")
