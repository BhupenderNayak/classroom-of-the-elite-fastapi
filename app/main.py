from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from typing import List
from .models import Student, StudentCreate, StudentUpdate
from .store import (
    list_students,
    get_student,
    create_student,
    update_student,
    expel_student,
)
import asyncio
import json
from pathlib import Path
from datetime import datetime
import random
import aiofiles

app = FastAPI(title="Classroom of the Elite")

EVAL_LOG = Path("evaluation_log.json")
EVAL_LOCK = asyncio.Lock()


async def append_eval_log(entry: dict):
    async with EVAL_LOCK:
        if not EVAL_LOG.exists():
            async with aiofiles.open(EVAL_LOG, "w", encoding="utf-8") as f:
                await f.write("[]")
        async with aiofiles.open(EVAL_LOG, "r+", encoding="utf-8") as f:
            text = await f.read()
            arr = json.loads(text) if text.strip() else []
            arr.append(entry)
            await f.seek(0)
            await f.write(json.dumps(arr, default=str, indent=2))
            await f.truncate()


# background task: simulate teacher evaluation and adjust score
async def _simulate_evaluation(student_id: int, reason: str | None = None):
    # simulate a delay (ex: teacher evaluation)
    await asyncio.sleep(3)
    # compute a small random change: -5..+10
    delta = random.randint(-5, 10)
    # load student, update if exists
    from .store import get_student, update_student

    student = await get_student(student_id)
    if not student:
        return

    new_score = max(0, min(100, student.score + delta))
    await update_student(student_id, {"score": new_score})

    entry = {
        "student_id": student_id,
        "delta": delta,
        "new_score": new_score,
        "reason": reason,
        "evaluated_at": datetime.now().isoformat(),
    }
    await append_eval_log(entry)


@app.post("/students/", response_model=Student, status_code=201)
async def api_create_student(payload: StudentCreate):
    return await create_student(payload)


@app.get("/students/", response_model=List[Student])
async def api_list_students(limit: int = Query(100, ge=1, le=1000)):
    students = await list_students()
    return students[:limit]


@app.get("/students/{student_id}", response_model=Student)
async def api_get_student(student_id: int):
    student = await get_student(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    return student


@app.put("/students/{student_id}", response_model=Student)
async def api_update_student(student_id: int, payload: StudentUpdate):
    patched = payload.model_dump(exclude_none=True)
    if not patched:
        raise HTTPException(400, "No fields to update")
    updated = await update_student(student_id, patched)
    if not updated:
        raise HTTPException(404, "Student not found")
    return updated


@app.post("/students/{student_id}/evaluate", response_model=dict)
async def api_evaluate_student(student_id: int, background_tasks: BackgroundTasks, reason: str | None = None):
    student = await get_student(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    # fire-and-forget background evaluation
    background_tasks.add_task(_simulate_evaluation, student_id, reason)
    return {"detail": "Evaluation scheduled", "student": student.model_dump()}


@app.post("/students/{student_id}/expel")
async def api_expel_student(student_id: int):
    ok = await expel_student(student_id)
    if not ok:
        raise HTTPException(404, "Student not found")
    return {"detail": "Student expelled"}


@app.get("/evaluations")
async def api_get_evaluations():
    if not EVAL_LOG.exists():
        return []
    async with aiofiles.open(EVAL_LOG, "r", encoding="utf-8") as f:
        text = await f.read()
        return json.loads(text) if text.strip() else []
