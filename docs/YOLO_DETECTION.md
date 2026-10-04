# YOLO Detection Module (Step 3)

This module adds AI-based object detection to the IBVAP pipeline using Ultralytics YOLOv8/11.

## Architecture
The system employs an abstract `BaseDetector` interface to decouple the frame pipeline from Ultralytics. The implementation `YOLODetector` handles loading the model and wrapping predictions into a domain-specific `DetectionResult` Pydantic model. 

```
Frame -> YOLODetector -> DetectionResult -> Downstream AI modules
```

## Model Used
The default model is `yolo11n.pt` (configurable via `.env`). The model is loaded once upon initialization of a camera pipeline.

## Configuration
The following environment variables control YOLO behavior:
- `YOLO_MODEL`: Path or name of the model weights (default: `yolo11n.pt`)
- `YOLO_CONFIDENCE`: Minimum confidence threshold (default: `0.40`)
- `YOLO_IOU`: NMS Intersection-over-Union threshold (default: `0.45`)
- `YOLO_DEVICE`: Device to run inference on (`cpu`, `cuda`, default: `cpu`)
- `DETECTION_CLASSES`: Comma-separated target classes (default: `person,car,motorcycle,bus,truck`)

## Supported Classes
The module maps COCO classes to targeted target classes and drops unrelated objects. Current defaults focus on human and vehicle detection.

## CPU/GPU Behavior
The prototype defaults to `cpu`. If a CUDA-enabled machine is used, `YOLO_DEVICE` can be changed to `cuda:0`.

## Testing & Visualization
The pipeline periodically saves annotated frames with bounding boxes and confidence labels to `outputs/detections/` to aid in debugging and validation.

## Next Steps
In Step 4, the output of `YOLODetector` (`DetectionResult` objects) will be passed to a multi-object tracker to assign persistent IDs and handle occlusion.
