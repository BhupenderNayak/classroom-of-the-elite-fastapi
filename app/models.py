from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClassSection(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class StudentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z ]+$")
    class_section: ClassSection
    score: int = Field(0, ge=0, le=100)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[A-Za-z ]+$")
    class_section: Optional[ClassSection] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    is_expelled: Optional[bool] = None


class Student(StudentBase):
    id: int
    is_expelled: bool = False
