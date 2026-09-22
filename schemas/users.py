from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from identity import validate_password_bytes


class UserCreate(BaseModel):
    first_name: str = Field(
        min_length=1,
        max_length=50,
    )
    last_name: str = Field(
        min_length=1,
        max_length=50,
    )
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=72,
    )

    @field_validator("password")
    @classmethod
    def validate_bcrypt_compatibility(cls, value: str):
        return validate_password_bytes(value)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    credit_score: int

    model_config = ConfigDict(from_attributes=True)
