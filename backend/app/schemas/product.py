"""Product request/response schemas."""

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str
    price: str = Field(pattern=r"^\d+(\.\d{1,2})?$")
    stock: int = Field(ge=0)
    description: str | None = None
    image_url: str | None = None


class ProductUpdateRequest(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    price: str | None = Field(default=None, pattern=r"^\d+(\.\d{1,2})?$")
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str
    price: str
    stock: int
    image_url: str | None = None
    is_returnable: bool
    version: int
