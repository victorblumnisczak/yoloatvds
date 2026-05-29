from dataclasses import dataclass
from typing import Iterable
from ultralytics import YOLO
from services.logging_config import get_logger

log = get_logger("agrovision.detector")


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2


class ObjectDetector:
    def __init__(self, model_path: str, confidence_threshold: float,
                 target_classes: Iterable[str]):
        self.model = YOLO(model_path)
        self.confidence = confidence_threshold
        self.target = set(target_classes)
        log.info("ObjectDetector carregado: %s (conf=%s, classes=%s)",
                 model_path, confidence_threshold, sorted(self.target))

    def detect(self, frame) -> list[Detection]:
        results = self.model(frame, conf=self.confidence, verbose=False)[0]
        out: list[Detection] = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]
            if label not in self.target:
                continue
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            out.append(Detection(label=label, confidence=conf, bbox=(x1, y1, x2, y2)))
        return out
