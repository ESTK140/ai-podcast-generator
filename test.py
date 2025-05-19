import requests

BASE_URL = "http://localhost:8001"

def test_all_steps():
    # STEP 1
    res = requests.post(f"{BASE_URL}/step1", json={
        "youtube_url": "https://youtu.be/mkZuB5NNEWM?si=UYfVjY2kcalsS6Ou"
    })
    assert res.status_code == 200
    data = res.json()
    session_id = data["session_id"]
    print("STEP1 Session ID:", session_id)

    # STEP 2
    res2 = requests.post(f"{BASE_URL}/step2", json={
        "session_id": session_id,
        "question": 
        """ 
        การเปลี่นแปลงนโยบายการจ้างงานจะมีผลยังไงกับอุตสาหกรรมที่เราทำงานอยู่บ้าง?
        """
    })
    assert res2.status_code == 200
    print("STEP2:", res2.json())
    res2 = requests.post(f"{BASE_URL}/step2", json={
        "session_id": session_id,
        "question": " เราจะเตรียมตัวอย่างไรสำหรับการเปลี่ยนแปลงทางเศรษฐกิจที่อาจเกิดจากนโยบายใหม่?"
    })

    assert res2.status_code == 200
    print("STEP2:", res2.json())

    # STEP 3
    res3 = requests.post(f"{BASE_URL}/step3", json={"session_id": session_id})
    assert res3.status_code == 200
    print("STEP3:", res3.json())

if __name__ == "__main__":
    test_all_steps()
