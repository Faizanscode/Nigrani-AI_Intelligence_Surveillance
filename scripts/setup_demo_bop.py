import json
import os
import uuid

DATA_FILE = "data/cameras.json"

def load_cameras():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_cameras(cameras):
    with open(DATA_FILE, "w") as f:
        json.dump(cameras, f, indent=2)

def main():
    cameras = load_cameras()

    # The BOP Simulation Coordinates around Punjab Border
    demo_cameras = [
        {
            "id": "CAM-01",
            "name": "Main Gate (ANPR)",
            "type": "file",
            "url": "dummy.mp4",
            "latitude": 31.6330,
            "longitude": 74.8710,
            "border_sector": "BOP-ALPHA-01",
            "border_state": "Punjab",
            "border_region": "NORTH",
            "bop_name": "Main BOP Gate"
        },
        {
            "id": "CAM-02",
            "name": "Border Road (Vehicle Tracking)",
            "type": "file",
            "url": "dummy.mp4",
            "latitude": 31.6350,
            "longitude": 74.8750,
            "border_sector": "BOP-ALPHA-01",
            "border_state": "Punjab",
            "border_region": "NORTH",
            "bop_name": "Border Checkpost"
        },
        {
            "id": "CAM-03",
            "name": "Perimeter Fence (Intrusion)",
            "type": "file",
            "url": "dummy.mp4",
            "latitude": 31.6400,
            "longitude": 74.8700,
            "border_sector": "BOP-ALPHA-01",
            "border_state": "Punjab",
            "border_region": "NORTH",
            "bop_name": "Fence Zone A"
        },
        {
            "id": "CAM-04",
            "name": "Watch Tower (Loitering)",
            "type": "file",
            "url": "dummy.mp4",
            "latitude": 31.6420,
            "longitude": 74.8800,
            "border_sector": "BOP-ALPHA-01",
            "border_state": "Punjab",
            "border_region": "NORTH",
            "bop_name": "Tower 1"
        },
        {
            "id": "CAM-05",
            "name": "Vehicle Checkpoint (Face Recog)",
            "type": "file",
            "url": "dummy.mp4",
            "latitude": 31.6380,
            "longitude": 74.8780,
            "border_sector": "BOP-ALPHA-01",
            "border_state": "Punjab",
            "border_region": "NORTH",
            "bop_name": "Checkpoint Alpha"
        }
    ]

    for c in demo_cameras:
        print(f"Adding/Updating {c['id']} - {c['name']}")
        cameras[c["id"]] = c

    save_cameras(cameras)
    print("Demo cameras configured in data/cameras.json")

if __name__ == '__main__':
    main()
