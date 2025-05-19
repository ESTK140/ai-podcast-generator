from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from podcast_pipeline import (
    step1_initialize_and_generate_opening,
    step2_continue_conversation,
    step3_finalize_and_generate_audio
)

import os

app = FastAPI()

# Mount media directory (ให้ Streamlit หรือ browser โหลดไฟล์ media ได้)
MEDIA_DIR = os.path.join(os.getcwd(), "downloads")
app.mount("/downloads", StaticFiles(directory=MEDIA_DIR), name="downloads")


class Step1Request(BaseModel):
    youtube_url: str

class Step2Request(BaseModel):
    session_id: str
    question: str

class Step3Request(BaseModel):
    session_id: str


@app.post("/step1")
def api_step1(req: Step1Request):
    result = step1_initialize_and_generate_opening(req.youtube_url)
    return result

from fastapi import UploadFile, File
import shutil
import uuid

@app.post("/step1/upload")
def api_step1_upload(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}_{file.filename}"
    save_path = os.path.join(MEDIA_DIR, filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = step1_initialize_and_generate_opening(save_path)
    return result



@app.post("/step2")
def api_step2(req: Step2Request):
    try:
        script, questions = step2_continue_conversation(req.session_id, req.question)
        return {
            "session_id": req.session_id,
            "script": script,
            "suggested_questions": questions
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/step3")
def api_step3(req: Step3Request):
    try:
        audio_path = step3_finalize_and_generate_audio(req.session_id)

        # 👉 สร้าง URL path ที่ Streamlit จะใช้ได้
        filename = os.path.basename(audio_path)
        audio_url = f"/media/{filename}"

        # optional: ตรวจสอบว่ามี video ไหม
        video_path = audio_path.replace(".wav", ".mp4")
        video_url = None
        if os.path.exists(video_path):
            video_url = f"/media/{os.path.basename(video_path)}"

        return {
            "session_id": req.session_id,
            "audio_path": audio_url,
            "video_path": video_url
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

