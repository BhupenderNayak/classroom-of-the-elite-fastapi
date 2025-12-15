import json
import asyncio
from pathlib import Path
from typing import List, Optional

import aiofiles

from .models import Student, StudentCreate
from datetime import datetime

STUDENTS_FILE = Path("students.json")
LOCK = asyncio.Lock()


async def _read_file() -> List[dict]:
    if not STUDENTS_FILE.exists():
        return []
    async with aiofiles.open(STUDENTS_FILE, "r", encoding="utf-8") as f:
        text = await f.read()
        if not text.strip():
            return []
        return json.loads(text)


async def _write_file(data: List[dict]) -> None:
    async with LOCK:
        async with aiofiles.open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, default=str, ensure_ascii=False, indent=2))


async def list_students() -> List[Student]:
    data = await _read_file()
    # sort descending by score
    data.sort(key=lambda d: d.get("score", 0), reverse=True)
    return [Student.model_validate(d) for d in data]


async def get_student(student_id: int) -> Optional[Student]:
    data = await _read_file()
    for d in data:
        if d.get("id") == student_id:
            return Student.model_validate(d)
    return None


async def create_student(payload: StudentCreate) -> Student:
    data = await _read_file()
    next_id = max((d.get("id", 0) for d in data), default=0) + 1
    obj = Student(id=next_id, **payload.model_dump(), is_expelled=False)
    data.append(obj.model_dump())
    await _write_file(data)
    return obj


async def update_student(student_id: int, patch: dict) -> Optional[Student]:
    data = await _read_file()
    for i, d in enumerate(data):
        if d.get("id") == student_id:
            d.update(patch)
            data[i] = d
            await _write_file(data)
            return Student.model_validate(d)
    return None


async def expel_student(student_id: int) -> bool:
    data = await _read_file()
    changed = False
    for i, d in enumerate(data):
        if d.get("id") == student_id:
            d["is_expelled"] = True
            data[i] = d
            changed = True
            break
    if changed:
        await _write_file(data)
    return changed
