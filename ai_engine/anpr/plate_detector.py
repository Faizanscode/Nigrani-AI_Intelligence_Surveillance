import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import List
from .models import PlateDetection
import random

class BasePlateDetector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray) -> List[PlateDetection]:
        pass

class OpenCVPlateDetector(BasePlateDetector):
    """
    Real plate detector for vehicle crops using color segmentation (yellow/white)
    and contour geometry, with bumper region localization.
    """
    def __init__(self, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold

    def detect(self, image: np.ndarray) -> List[PlateDetection]:
        if image is None or image.size == 0:
            return []

        h, w = image.shape[:2]
        if h < 30 or w < 30:
            return []

        candidates = []

        # 1. License plates on cars/trucks/buses are located in the lower 60% of the vehicle
        bumper_y1 = int(h * 0.40)
        bumper = image[bumper_y1:h, :]
        bh, bw = bumper.shape[:2]

        if bh > 10 and bw > 10:
            # 2a. Check for Indian Commercial (Yellow) License Plates in HSV
            hsv = cv2.cvtColor(bumper, cv2.COLOR_BGR2HSV)
            lower_yellow = np.array([12, 50, 50])
            upper_yellow = np.array([38, 255, 255])
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

            yellow_contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in yellow_contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = cw / float(ch) if ch > 0 else 0
                area = cw * ch
                if 1.5 <= aspect <= 6.0 and area >= 200:
                    px1 = max(0, x - 5)
                    py1 = max(0, bumper_y1 + y - 5)
                    px2 = min(w, x + cw + 5)
                    py2 = min(h, bumper_y1 + y + ch + 5)
                    candidates.append(PlateDetection(bbox=[px1, py1, px2, py2], confidence=0.88))

            # 2b. High-contrast / Edge contour detection for white plates
            gray_bumper = cv2.cvtColor(bumper, cv2.COLOR_BGR2GRAY)
            sobel = cv2.Sobel(gray_bumper, cv2.CV_8U, 1, 0, ksize=3)
            _, thresh = cv2.threshold(sobel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            edge_contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in edge_contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = cw / float(ch) if ch > 0 else 0
                area = cw * ch
                if 1.8 <= aspect <= 5.5 and area >= 300 and cw >= int(bw * 0.15):
                    px1 = max(0, x - 4)
                    py1 = max(0, bumper_y1 + y - 4)
                    px2 = min(w, x + cw + 4)
                    py2 = min(h, bumper_y1 + y + ch + 4)
                    candidates.append(PlateDetection(bbox=[px1, py1, px2, py2], confidence=0.75))

        # 3. Always include bumper candidate as high-confidence fallback
        # EasyOCR's built-in CRAFT text detector will locate and read characters inside the bumper crop
        bw_cand = int(w * 0.75)
        bh_cand = int(h * 0.45)
        bx1 = (w - bw_cand) // 2
        by1 = int(h * 0.50)
        bx2 = bx1 + bw_cand
        by2 = min(h, by1 + bh_cand)
        candidates.append(PlateDetection(bbox=[bx1, by1, bx2, by2], confidence=0.60))

        return candidates

class MockPlateDetector(BasePlateDetector):
    """
    Simulates a plate detector for prototyping without downloading huge models.
    """
    def __init__(self, confidence_threshold=0.4):
        self.confidence_threshold = confidence_threshold

    def detect(self, image: np.ndarray) -> List[PlateDetection]:
        h, w = image.shape[:2]
        if random.random() < 0.1:
            return []
        pw, ph = int(w * 0.4), int(h * 0.15)
        px1 = (w - pw) // 2
        py1 = h - ph - int(h * 0.1)
        px2 = px1 + pw
        py2 = py1 + ph
        conf = random.uniform(0.6, 0.99)
        if conf >= self.confidence_threshold:
            return [PlateDetection(bbox=[px1, py1, px2, py2], confidence=conf)]
        return []

