import os
import cv2
import time
import uuid
import threading
from datetime import datetime
from collections import defaultdict

from services.config import (
    CAMERA_SOURCE, MODEL_PATH, CONFIDENCE_THRESHOLD, SAVE_DIR,
    TARGET_CLASSES, MIN_CONSECUTIVE_FRAMES, ALERT_COOLDOWN_SECONDS,
    CAMERA_RECONNECT_SECONDS,
)
import services.camera_pool as camera_pool
from services.event_repository import save_event
from services.logging_config import get_logger
from services.detector import ObjectDetector, Detection

log = get_logger("agrovision.video")


class VideoMonitor:
    def __init__(self):
        self._last_frame = None
        self._lock = threading.Lock()
        self._connected = False
        self._running = False
        self._detection_state: dict = defaultdict(int)
        self._last_alert_time: dict = defaultdict(float)
        # Fonte ativa; definida em _run() — pode ser URL do pool ou override do .env
        self._active_source: str | int | None = CAMERA_SOURCE
        self._detector = ObjectDetector(MODEL_PATH, CONFIDENCE_THRESHOLD, TARGET_CLASSES)

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def get_last_frame(self):
        with self._lock:
            return self._last_frame.copy() if self._last_frame is not None else None

    def has_frame(self) -> bool:
        with self._lock:
            return self._last_frame is not None

    def status(self) -> dict:
        src = self._active_source
        source_type = (
            "stream" if isinstance(src, str) and src.startswith("http") else "webcam"
        )
        return {
            "online": self._running,
            "connected": self._connected,
            "has_live_frame": self.has_frame(),
            "source_type": source_type,
            "source": str(src) if src is not None else "pool (aguardando início)",
        }

    def _should_alert(self, label: str) -> bool:
        now = time.time()
        if now - self._last_alert_time[label] >= ALERT_COOLDOWN_SECONDS:
            self._last_alert_time[label] = now
            return True
        return False

    def iter_mjpeg(self):
        while self._running:
            frame = self.get_last_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes() + b"\r\n"
            )
            time.sleep(0.05)

    def _run(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        if CAMERA_SOURCE is None:
            self._active_source = camera_pool.pick_random()
            log.info("Pool ativo. Câmera selecionada: %s", self._active_source)
        else:
            self._active_source = CAMERA_SOURCE
        while self._running:
            try:
                self._capture_loop()
            except Exception:
                log.exception("VideoMonitor: erro inesperado, reiniciando em 5s")
                time.sleep(5)

    def _capture_loop(self):
        consecutive_failures = 0

        while self._running:
            cap = cv2.VideoCapture(self._active_source)
            if not cap.isOpened():
                consecutive_failures += 1
                log.warning(
                    "Falha ao abrir '%s' (%d/3). Tentando novamente em %ds...",
                    self._active_source, consecutive_failures, CAMERA_RECONNECT_SECONDS,
                )
                if CAMERA_SOURCE is None and consecutive_failures >= 3:
                    self._active_source = camera_pool.next_after_failure(
                        str(self._active_source)
                    )
                    consecutive_failures = 0
                    log.info("Trocando para câmera do pool: %s", self._active_source)
                time.sleep(CAMERA_RECONNECT_SECONDS)
                continue

            consecutive_failures = 0
            self._connected = True
            log.info("Câmera conectada: %s", self._active_source)

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self._connected = False
                    log.warning(
                        "Stream perdido. Reconectando em %ds...", CAMERA_RECONNECT_SECONDS
                    )
                    time.sleep(CAMERA_RECONNECT_SECONDS)
                    break

                detections = self._detector.detect(frame)
                current_labels: set = set()
                frame_best_conf: dict[str, float] = defaultdict(float)

                for det in detections:
                    x1, y1, x2, y2 = det.bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame, f"{det.label} {det.confidence:.0%}",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                    )
                    current_labels.add(det.label)
                    if det.confidence > frame_best_conf[det.label]:
                        frame_best_conf[det.label] = det.confidence

                for label in list(self._detection_state.keys()):
                    if label not in current_labels:
                        self._detection_state[label] = 0

                for label in current_labels:
                    self._detection_state[label] += 1
                    if (
                        self._detection_state[label] >= MIN_CONSECUTIVE_FRAMES
                        and self._should_alert(label)
                    ):
                        conf = frame_best_conf[label]
                        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        event_id = uuid.uuid4().hex[:8]
                        img_filename = f"{now_str}_{label}_{event_id}.jpg"
                        img_path = os.path.join(SAVE_DIR, img_filename)
                        cv2.imwrite(img_path, frame)
                        save_event(label, conf, f"/static/captures/{img_filename}")
                        self._detection_state[label] = 0
                        log.info("Alerta: %s conf=%.2f", label, conf)

                with self._lock:
                    self._last_frame = frame.copy()

            cap.release()
