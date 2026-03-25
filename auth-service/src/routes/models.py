from pydantic import BaseModel


class NotAuthorized(BaseModel):
    detail: str
