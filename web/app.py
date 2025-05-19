import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# --- โหลดค่าจาก .env ---
load_dotenv()

API_BASE = os.getenv("API_BASE") 
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(page_title="Podcast Generator", layout="wide")

st.title("🎙️ AI Podcast Workspace")
st.markdown("---")

# --- Load session list ---
@st.cache_data
def load_sessions():
    url = f"{SUPABASE_URL}/rest/v1/podcast_scripts"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    res = requests.get(url, headers=headers)
    return res.json() if res.ok else []

sessions = load_sessions()

# --- Sidebar Workspace ---
st.sidebar.title("📂 Podcast Sessions")
if st.sidebar.button("🔄 Refresh Sessions"):
    st.cache_data.clear()
    st.rerun()


selected = st.sidebar.radio("Select Session", options=[s['session_id'] for s in sessions] + ["➕ New Session"])

# --- Show Selected Session ---
if selected != "➕ New Session":
    session = next((s for s in sessions if s['session_id'] == selected), None)

    if session:
        st.subheader(f"🧾 Session ID: {session['session_id']}")
        st.markdown(f"⏱️ Timestamp: `{session['timestamp']}`")
        st.markdown("### 💬 Script")
        script = json.loads(session["script"])
        for line in script:
            st.write(f"**{line['speaker']}**: {line['text']}")

        if session.get("audio_path"):
            st.markdown("### 🔊 Audio Preview")
            audio_file = session["audio_path"]
            st.audio(audio_file)

# --- Create new session ---
# --- Create new session ---
else:
    st.subheader("✨ Start a New Podcast Session")

    # แสดง YouTube และ Upload ในพื้นที่เดียวกัน
    col1, col2 = st.columns(2)
    with col1:
        youtube_url = st.text_input("🔗 วางลิงก์ YouTube เพื่อเริ่ม")
    with col2:
        uploaded_file = st.file_uploader("📤 หรืออัปโหลดวิดีโอ/เสียง (.wav)", type=["mp4", "mov", "avi", "mkv", "webm", "wav"])

    # Initial session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
        st.session_state.script_blocks = []
        st.session_state.suggestions = []
        st.session_state.summary = ""
        st.session_state.question_input = ""

    # 🚫 ป้องกันไม่ให้กรอกทั้ง YouTube และ Upload พร้อมกัน
    if youtube_url and uploaded_file:
        st.warning("กรุณาเลือกอย่างใดอย่างหนึ่ง: YouTube หรืออัปโหลดไฟล์")

    # ▶️ YouTube Flow
    elif youtube_url and st.button("▶️ Generate from YouTube"):
        with st.spinner("🧠 Step1: วิเคราะห์วิดีโอจาก YouTube"):
            res1 = requests.post(f"{API_BASE}/step1", json={"youtube_url": youtube_url}).json()
        st.session_state.session_id = res1["session_id"]
        st.session_state.summary = res1["summary"]
        st.session_state.suggestions = res1["suggested_questions"].strip().splitlines()
        st.session_state.script_blocks = []
        st.success("✅ Step1 เสร็จแล้ว")

    # ▶️ Upload Flow (รองรับทั้งวิดีโอและเสียง)
    elif uploaded_file is not None and st.button("▶️ Generate from File"):
        filetype = uploaded_file.type
        if not (filetype.startswith("video/") or filetype == "audio/wav"):
            st.error("❌ รองรับเฉพาะวิดีโอหรือไฟล์เสียง .wav เท่านั้น")
        else:
            # แสดง preview
            if filetype.startswith("video/"):
                st.video(uploaded_file)
            else:
                st.audio(uploaded_file)

            with st.spinner("🧠 Step1: วิเคราะห์ไฟล์ที่อัปโหลด"):
                files = {"file": (uploaded_file.name, uploaded_file, filetype)}
                response = requests.post(f"{API_BASE}/step1/upload", files=files)

                if response.ok:
                    res1 = response.json()
                    st.session_state.session_id = res1["session_id"]
                    st.session_state.summary = res1["summary"]
                    st.session_state.suggestions = res1["suggested_questions"].strip().splitlines()
                    st.session_state.script_blocks = []
                    st.success("✅ Step1 เสร็จแล้ว")
                else:
                    st.error("❌ การอัปโหลดล้มเหลว: " + response.text)



    if st.session_state.session_id:
        st.markdown("### 🧠 Summary")
        st.code(st.session_state.summary)

        st.markdown("### 💡 Suggested Questions")
        for q in st.session_state.suggestions:
            if q.strip():
                st.code(q.strip(), language="markdown")

        st.markdown("### 📝 Script Conversation")
        for i, block in enumerate(st.session_state.script_blocks):
            st.markdown(f"#### 🗣️ Q{i+1}: {block['question']}")
            st.code(block["script"])
            st.markdown("🔁 คำถามต่อยอด:")
            for sug in block["suggestions"]:
                if sug.strip():
                    st.code(sug.strip(), language="markdown")

        st.divider()

        # 🔻 Input & Button อยู่ล่างสุด
        st.markdown("### ✍️ ถามคำถามใหม่เพื่อขยาย Script")
        # 📝 รับค่าจาก text_input และเก็บไว้ใน session_state
        st.text_input("💬 พิมพ์คำถาม", key="question_input")

        # ⏺️ ใช้ค่าจาก session_state โดยตรง
        if st.button("💬 เพิ่ม Script (Step2)"):
            question = st.session_state["question_input"].strip()

            if not question:
                st.warning("กรุณาพิมพ์คำถามก่อนส่ง")
            else:
                with st.spinner("📚 กำลังสร้าง Script..."):
                    res2 = requests.post(f"{API_BASE}/step2", json={
                        "session_id": st.session_state.session_id,
                        "question": question
                    }).json()

                st.session_state.script_blocks.append({
                    "question": question,
                    "script": res2["script"],
                    "suggestions": res2["suggested_questions"].strip().splitlines()
                })

                st.session_state.suggestions = res2["suggested_questions"].strip().splitlines()
                st.success("✅ Script ถูกเพิ่มแล้ว")


                st.rerun()



        st.divider()

        # Step 3 (สร้างเสียง)
        if st.button("🎧 สร้างเสียงทั้งหมด (Step3)"):
            with st.spinner("🔊 กำลังสร้างเสียงและวิดีโอ..."):
                res3 = requests.post(f"{API_BASE}/step3", json={"session_id": st.session_state.session_id}).json()
            st.success("✅ Step3 เสร็จแล้ว")

            st.audio(f"{API_BASE}{res3['audio_path']}")
            if res3.get("video_path"):
                st.video(f"{API_BASE}{res3['video_path']}")
            st.balloons()

