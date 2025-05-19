import subprocess
import threading
import time

def run_backend():
    subprocess.run(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"])

def run_frontend():
    # ✅ ชี้ path ถูกต้องไปยัง web/app.py
    subprocess.run([
    "streamlit", "run", "web/app.py",
    "--server.address=0.0.0.0",
    "--server.port=8501",
    "--server.maxUploadSize=1000"  # ✅ เพิ่มตรงนี้
])


# รัน backend ใน thread แยก
backend_thread = threading.Thread(target=run_backend)
backend_thread.start()

# รอ backend สตาร์ทก่อน
time.sleep(2)

# รัน frontend
run_frontend()
