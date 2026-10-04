import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. Add the camera
camera_data = {
    "name": "Loitering Test Video",
    "type": "file",
    # Replace this with the path to ANY .mp4 file on your computer
    "source": r"C:\Users\iamfa\Downloads\8mp-4k-dahua-cctv-system-sample-video-night-time-ytmp4.savetube.vip.mp4" 
}

print("Adding camera...")
res = requests.post(f"{BASE_URL}/cameras", json=camera_data)
data = res.json()
print(data)

if "id" in data:
    cam_id = data["id"]
    time.sleep(1)

    # 2. Start the camera
    print(f"\nStarting camera {cam_id}...")
    start_res = requests.post(f"{BASE_URL}/cameras/{cam_id}/start")
    print(start_res.json())
else:
    print("Failed to add camera")
