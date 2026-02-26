from pydantic import BaseModel


class UserCreate(BaseModel):
    login: str
    email: str
    first_name: str
    last_name: str
    password: str


class LoginPayload(BaseModel):
    login: str
    password: str
