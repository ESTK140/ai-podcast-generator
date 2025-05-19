import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="🎧 Workspace", layout="wide")
st.title("📁 Podcast Workspace")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

@st.cache_data(show_spinner=False)
def load_sessions():
    url = f"{SUPABASE_URL}/rest/v1/podcast_scripts?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    res = requests.get(url, headers=headers)
    return res.json() if res.ok else []

sessions = load_sessions()

if sessions:
    for session in sessions[::-1]:
        with st.expander(f"🗂️ Session: {session['session_id']} — {session['timestamp']}"):
            st.markdown("### 🧠 Summary")
            st.code(session.get("suggested_questions", ""), language="markdown")

            st.markdown("### 💬 Script")
            script = json.loads(session.get("script", "[]"))
            for line in script:
                st.write(f"**{line['speaker']}**: {line['text']}")

            if session.get("audio_path"):
                audio_url = f"{API_BASE}{session['audio_path']}"
                st.markdown("### 🔊 Audio")
                st.audio(audio_url)

            if session.get("video_path"):
                video_url = f"{API_BASE}{session['video_path']}"
                st.markdown("### 🎞️ Video")
                st.video(video_url)
else:
    st.info("ยังไม่มี session ใด ๆ")
