import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="➕ Create Podcast", layout="wide")
st.title("➕ สร้าง Podcast ใหม่")

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
    st.session_state.summary = ""
    st.session_state.script_blocks = []

youtube_url = st.text_input("🔗 วางลิงก์ YouTube เพื่อเริ่มสร้าง")

if st.button("🎬 เริ่ม Step 1"):
    if not youtube_url:
        st.warning("กรุณาใส่ลิงก์ YouTube")
    else:
        with st.spinner("กำลังประมวลผล..."):
            res1 = requests.post(f"{API_BASE}/step1", json={"youtube_url": youtube_url})
            if res1.status_code == 200:
                data1 = res1.json()
                st.session_state.session_id = data1["session_id"]
                st.session_state.summary = data1["summary"]
                st.session_state.script_blocks = []
                st.success("Step 1 เสร็จแล้ว ✅")
                st.code(data1["summary"])
            else:
                st.error("Step 1 ล้มเหลว")

if st.session_state.session_id:
    st.markdown("### ✍️ ถามคำถามต่อเพื่อขยาย Script")
    question = st.text_input("ถามคำถามเพิ่มเติม...", key="followup_q")
    if st.button("💬 เพิ่ม Script (Step 2)"):
        if not question:
            st.warning("พิมพ์คำถามก่อนกดส่ง")
        else:
            res2 = requests.post(f"{API_BASE}/step2", json={
                "session_id": st.session_state.session_id,
                "question": question
            })
            if res2.status_code == 200:
                data2 = res2.json()
                st.session_state.script_blocks.append({
                    "question": question,
                    "script": data2["script"],
                    "suggestions": data2["suggested_questions"]
                })
                st.success("Script ใหม่ถูกเพิ่มแล้ว ✅")
            else:
                st.error("Step 2 ล้มเหลว")

    for i, block in enumerate(st.session_state.script_blocks):
        st.markdown(f"#### 🗣️ Q{i+1}: {block['question']}")
        st.code(block["script"])
        st.markdown("🔁 คำถามแนะนำ:")
        st.code(block["suggestions"], language="markdown")

    if st.button("🎧 สร้างเสียงทั้งหมด (Step 3)"):
        res3 = requests.post(f"{API_BASE}/step3", json={"session_id": st.session_state.session_id})
        if res3.status_code == 200:
            data3 = res3.json()
            audio_url = f"{API_BASE}{data3['audio_path']}"
            st.audio(audio_url)
            if data3.get("video_path"):
                video_url = f"{API_BASE}{data3['video_path']}"
                st.video(video_url)
            st.success("สร้างเสียง/วิดีโอเรียบร้อย ✅")
        else:
            st.error("Step 3 ล้มเหลว")
