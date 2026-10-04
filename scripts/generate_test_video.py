import cv2
import numpy as np
import os
import time

def generate_test_video(output_path: str, width: int = 640, height: int = 480, fps: int = 30, duration_sec: int = 10):
    """
    Generates a synthetic test video with a moving rectangle (simulating a target)
    and timestamp/frame counter.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = fps * duration_sec
    rect_x = 0
    rect_y = height // 2
    rect_w = 50
    rect_h = 100
    
    speed_x = int(width / total_frames) + 1
    
    for i in range(total_frames):
        # Create a dark gray background simulating night/evening
        frame = np.ones((height, width, 3), dtype=np.uint8) * 50
        
        # Draw moving rectangle (simulating a person or vehicle)
        cv2.rectangle(frame, (rect_x, rect_y), (rect_x + rect_w, rect_y + rect_h), (0, 255, 0), -1)
        
        # Draw some static "fence" line
        cv2.line(frame, (width//2, 0), (width//2, height), (0, 0, 255), 2)
        
        # Overlay text
        cv2.putText(frame, f"Frame: {i}/{total_frames}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Camera: SIMULATED_01", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
        
        # Move rect
        rect_x += speed_x
        if rect_x > width:
            rect_x = 0
            
    out.release()
    print(f"Generated test video: {output_path} ({duration_sec}s, {total_frames} frames)")

if __name__ == "__main__":
    test_video_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'videos', 'test_border.mp4')
    generate_test_video(test_video_path)
