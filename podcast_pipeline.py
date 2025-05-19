import os
import json
import subprocess
import asyncio
import aiohttp
import requests
from datetime import datetime
from dotenv import load_dotenv
from pydub import AudioSegment
from openai import OpenAI
from supabase import create_client, Client

# --- ENV SETUP ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TRANSCRIBE_AUDIO_ENDPOINT = "http://100.76.219.70:8000/audio/transcibe_audio"
BOTNOI_VOICE_ENDPOINT = "http://100.76.219.70:8000/script/botnoi-voice"
VOICE_ID_A = "543"
VOICE_ID_B = "544"

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
AUDIO_LINE_DIR = os.path.join(DOWNLOAD_DIR, "audio_lines")
GPT_TOKEN = os.getenv("GPT_TOKEN")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_LINE_DIR, exist_ok=True)

openai_client = OpenAI(api_key=GPT_TOKEN)

# --- GLOBAL MEMORY ---
script_lines = []
chat_history = []

# --- Supabase ---
def save_script_to_supabase(session_id, script_lines, suggested_questions, audio_path=None):
    data = {
        "session_id": session_id,
        "script": json.dumps(script_lines, ensure_ascii=False),
        "suggested_questions": suggested_questions,
        "timestamp": datetime.now().isoformat()
    }
    if audio_path:
        data["audio_path"] = audio_path

    supabase.table("podcast_scripts").upsert(data, on_conflict=["session_id"]).execute()


def load_session_from_supabase(session_id):
    response = supabase.table("podcast_scripts").select("*").eq("session_id", session_id).execute()
    if response.data:
        data = response.data[0]
        return {
            "script_lines": json.loads(data["script"]),
            "suggested_questions": data.get("suggested_questions", "")
        }
    return None

# --- Utilities ---
def hash_url(url):
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()

def download_youtube_audio(youtube_url):
    video_id = hash_url(youtube_url)
    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.m4a")
    audio_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.wav")
    if not os.path.exists(audio_path):
        subprocess.run(["yt-dlp", "-f", "bestaudio[ext=m4a]", "-o", output_path, youtube_url], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", output_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path], check=True)
        os.remove(output_path)
    return audio_path

def transcribe_audio(audio_path, lang="th"):
    with open(audio_path, 'rb') as f:
        files = {'audios': (os.path.basename(audio_path), f, 'audio/wav')}
        data = {'language': lang}
        response = requests.post(TRANSCRIBE_AUDIO_ENDPOINT, files=files, data=data)
        response.raise_for_status()
        return response.json()

def summarize_for_podcast(transcript_text):
    prompt = f"""
ต่อไปนี้คือ transcript คำพูดทั้งหมดจากวิดีโอหนึ่ง ขอให้คุณทำหน้าที่เป็นนักเขียนสรุปเนื้อหา เพื่อเตรียมข้อมูลอ้างอิงสำหรับการสร้างรายการ Podcast

**เป้าหมายของคุณ**:
1. สรุปโดยรวม + แยกหัวข้อสำคัญ
2. คำพูดน่าสนใจ (Notable Quotes)

---
{transcript_text}
---
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def add_summary_to_history(summary_text):
    chat_history.clear()
    system_prompt = f"""
คุณคือผู้ช่วยสร้าง Podcast สองคน A และ B ที่พูดคุยกันอย่างเป็นธรรมชาติ ใช้ภาษาง่าย ลื่นไหล น่าฟัง และมีคำถามชวนคิดต่อในตอนท้าย

เนื้อหาที่ใช้สำหรับการพูดใน Podcast คือ:
{summary_text}
"""
    chat_history.insert(0, {"role": "system", "content": system_prompt})

def create_opening_from_summary(summary_text):
    prompt = f"""
ต่อไปนี้คือสรุปเนื้อหาสำคัญจากวิดีโอ:

{summary_text}

สร้างบทพูดเปิดรายการ Podcast โดยมีผู้ดำเนินรายการ 2 คน (เอวา และ สมพง) ที่พูดคุยเกริ่นนำประเด็นเหล่านี้ให้ชวนติดตาม โดยไม่ใช้คำทักทายแบบทั่วไป เช่น 'ยินดีต้อนรับ' หรือ 'สวัสดีครับ'

**รูปแบบ:** สลับพูด A: / B: 2–4 บรรทัด ใช้ภาษากระชับ ลื่นไหล
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    opening_script = response.choices[0].message.content.strip()
    lines = []
    for line in opening_script.splitlines():
        if line.startswith("A:"):
            lines.append({"speaker": "A", "text": line[2:].strip()})
        elif line.startswith("B:"):
            lines.append({"speaker": "B", "text": line[2:].strip()})
    return lines

def generate_podcast_script(question_input):
    previous_context = "".join([f"{line['speaker']}: {line['text']}\n" for line in script_lines[-8:]]) if script_lines else '(ยังไม่มีบทสนทนา)'
    chat_history.append({
        "role": "user",
        "content": f"""
หัวข้อ: {question_input}

ต่อจากบทสนทนาเดิม:
{previous_context}

สร้างบทพูด podcast สองคน สลับ A: / B: อย่างลื่นไหล 10–20 บรรทัด โดยเชื่อมโยงกับเนื้อหาเดิม ไม่ต้องทักทายหรือเริ่มใหม่ และให้ลงท้ายด้วย `### Suggested Follow-up Questions:` (คำถามอย่างน้อย 3 ข้อ)
"""
    })
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=chat_history
    )
    result = response.choices[0].message.content.strip()
    chat_history.append({"role": "assistant", "content": result})
    parts = result.split("### Suggested Follow-up Questions:")
    script_part = parts[0].split("### Podcast Script:")[-1].strip()
    suggestions = parts[1].strip() if len(parts) > 1 else ""

    for line in script_part.splitlines():
        if line.startswith("A:"):
            script_lines.append({"speaker": "A", "text": line[2:].strip()})
        elif line.startswith("B:"):
            script_lines.append({"speaker": "B", "text": line[2:].strip()})

    return script_part, suggestions

async def send_line_to_botnoi(line_text: str, voice_id: str, save_path: str):
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('voice_id', voice_id)
        data.add_field('script', line_text)
        async with session.post(BOTNOI_VOICE_ENDPOINT, data=data) as resp:
            with open(save_path, 'wb') as out_f:
                out_f.write(await resp.read())

def generate_voice_from_script_lines():
    async def run_all_tasks():
        tasks = []
        for i, line in enumerate(script_lines):
            voice_id = VOICE_ID_A if line['speaker'] == 'A' else VOICE_ID_B
            filename = f"{line['speaker']}_{i+1}.wav"
            save_path = os.path.join(AUDIO_LINE_DIR, filename)
            tasks.append(send_line_to_botnoi(line['text'], voice_id, save_path))
        await asyncio.gather(*tasks)
    asyncio.run(run_all_tasks())

def combine_voices_in_order(session_id):
    combined = AudioSegment.empty()
    for i, line in enumerate(script_lines):
        filename = f"{line['speaker']}_{i+1}.wav"
        file_path = os.path.join(AUDIO_LINE_DIR, filename)
        if os.path.exists(file_path):
            segment = AudioSegment.from_wav(file_path)
            combined += segment + AudioSegment.silent(duration=300)
    final_path = os.path.join(DOWNLOAD_DIR, f"podcast_final_{session_id}.wav")
    combined.export(final_path, format="wav")
    return final_path

def add_closing():
    previous_context = "".join([f"{line['speaker']}: {line['text']}\n" for line in script_lines[-20:]])
    prompt = f"""
ต่อไปนี้คือบทพูด podcast ที่ดำเนินมาจนถึงตอนท้าย:

{previous_context}

ขอให้คุณสร้าง **บทพูดปิดท้ายรายการ Podcast** ที่:
1. สรุปเนื้อหาหรือประเด็นที่พูดถึง
2. ปิดรายการอย่างเป็นกันเอง
3. เชิญชวนผู้ฟังให้ติดตาม แชร์ หรือแสดงความคิดเห็น

รูปแบบ: สลับ A: / B: อย่างลื่นไหล 4–6 บรรทัด
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    closing_script = response.choices[0].message.content.strip()
    for line in closing_script.splitlines():
        if line.startswith("A:"):
            script_lines.append({"speaker": "A", "text": line[2:].strip()})
        elif line.startswith("B:"):
            script_lines.append({"speaker": "B", "text": line[2:].strip()})
            
def step1_initialize_and_generate_opening(source: str):
    """
    source สามารถเป็น YouTube URL หรือ path ของ video/audio file (.mp4, .mov, .wav)
    """
    global script_lines, chat_history
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_lines.clear()
    chat_history.clear()

    # ตรวจว่าเป็น YouTube URL หรือ local path
    if source.startswith("http://") or source.startswith("https://"):
        audio_path = download_youtube_audio(source)
    elif os.path.exists(source):
        ext = os.path.splitext(source)[-1].lower()
        if ext == ".wav":
            # ใช้ไฟล์ wav ตรง ๆ ได้เลย
            audio_path = source
        else:
            # แปลง video → wav
            audio_path = os.path.join(DOWNLOAD_DIR, f"{session_id}.wav")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", source,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                audio_path
            ], check=True)
    else:
        raise ValueError("Invalid source path or URL")

    transcript = transcribe_audio(audio_path).get("transcribe_text", "")
    
    # ลบไฟล์เฉพาะกรณีที่เราเป็นคนแปลง
    if not source.endswith(".wav"):
        os.remove(audio_path)

    summary = summarize_for_podcast(transcript)
    add_summary_to_history(summary)
    opening_lines = create_opening_from_summary(summary)
    script_lines.extend(opening_lines)
    script_text, suggested_questions = generate_podcast_script("เริ่มต้นจากเรื่องไหนก่อนดี")
    save_script_to_supabase(session_id, script_lines, suggested_questions)

    return {
        "session_id": session_id,
        "summary": summary,
        "suggested_questions": suggested_questions
    }



def step2_continue_conversation(session_id, question):
    global script_lines, chat_history

    session_data = load_session_from_supabase(session_id)
    if not session_data:
        raise ValueError("Session not found")
    script_lines.clear()
    script_lines.extend(session_data["script_lines"])
    chat_history.clear()

    summary_text = " ".join([f"{line['speaker']}: {line['text']}" for line in script_lines[:6]])
    chat_history.append({
        "role": "system",
        "content": f"คุณคือผู้ช่วย Podcast\nเนื้อหาที่ผ่านมา:\n{summary_text}"
    })

    script_text, suggested_questions = generate_podcast_script(question)
    save_script_to_supabase(session_id, script_lines, suggested_questions)
    return script_text, suggested_questions

def step3_finalize_and_generate_audio(session_id):
    global script_lines

    session_data = load_session_from_supabase(session_id)
    if not session_data:
        raise ValueError("Session not found")

    script_lines.clear()
    script_lines.extend(session_data["script_lines"])

    add_closing()
    generate_voice_from_script_lines()
    audio_path = combine_voices_in_order(session_id)
    save_script_to_supabase(session_id, script_lines, session_data["suggested_questions"], audio_path)

    return audio_path

