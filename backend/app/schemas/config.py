from typing import Optional

from pydantic import BaseModel, ConfigDict


class AllowedUnitBase(BaseModel):
    code: str
    description: Optional[str] = None
    active: bool = True


class AllowedUnitCreate(AllowedUnitBase):
    pass


class AllowedUnitOut(AllowedUnitBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AllowedCountryBase(BaseModel):
    code: str
    name: str
    active: bool = True


class AllowedCountryCreate(AllowedCountryBase):
    pass


class AllowedCountryOut(AllowedCountryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
