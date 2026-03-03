import logging
import json
import io
from typing import List, Dict, Tuple, Optional

import dlib
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Student

logger = logging.getLogger(__name__)


class FaceRecognitionService:

    def __init__(self, tolerance: float = 0.6):
        self.tolerance = tolerance
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = None
        self.face_encoder = None
        self._simple_mode: bool = False

    def _ensure_models(self) -> None:
        """Загружает модели dlib при первом вызове. При отсутствии файлов переходит в простой режим."""
        if self.shape_predictor is not None:
            return
        try:
            self.shape_predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
            self.face_encoder = dlib.face_recognition_model_v1('dlib_face_recognition_resnet_model_v1.dat')
            logger.info("Модели dlib загружены успешно.")
        except Exception:
            logger.warning(
                "Модели dlib не найдены — система переходит в простой режим (только детекция лиц, без распознавания). "
                "Для полной функциональности скачайте:\n"
                "  http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2\n"
                "  http://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2"
            )
            self._simple_mode = True

    @property
    def is_recognition_available(self) -> bool:
        """True если модели загружены и распознавание работает корректно."""
        self._ensure_models()
        return not self._simple_mode

    def extract_face_encoding(self, image_bytes: bytes) -> Optional[List[float]]:
        """Возвращает 128-мерный вектор лица или None если лицо не найдено / простой режим."""
        self._ensure_models()
        if self._simple_mode:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)

            faces = self.detector(img_array, 1)
            if len(faces) == 0:
                return None

            face = faces[0]
            shape = self.shape_predictor(img_array, face)
            face_descriptor = self.face_encoder.compute_face_descriptor(img_array, shape)
            return list(face_descriptor)
        except Exception:
            logger.exception("Ошибка при извлечении face encoding")
            return None

    def extract_all_faces(self, image_bytes: bytes) -> List[List[float]]:
        """Возвращает список 128-мерных векторов всех найденных лиц.
        В простом режиме возвращает пустой список."""
        self._ensure_models()
        if self._simple_mode:
            return []

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_array = np.array(image)

            encodings = []
            for face in self.detector(img_array, 1):
                shape = self.shape_predictor(img_array, face)
                face_descriptor = self.face_encoder.compute_face_descriptor(img_array, shape)
                encodings.append(list(face_descriptor))
            return encodings
        except Exception:
            logger.exception("Ошибка при извлечении лиц из фото")
            return []

    def save_student_face(self, student: Student, image_bytes: bytes, db: Session) -> bool:
        """Сохраняет face encoding студента в БД.
        Принимает уже загруженный объект Student, не делает повторный запрос.
        Возвращает False если модели недоступны или лицо не найдено.
        """
        if self._simple_mode:
            logger.warning("save_student_face вызван в простом режиме — сохранение невозможно.")
            return False

        encoding = self.extract_face_encoding(image_bytes)
        if encoding is None:
            return False

        student.face_encoding = json.dumps(encoding)
        db.commit()
        return True

    def recognize_students(
        self,
        image_bytes: bytes,
        students: List[Student],
    ) -> Tuple[List[int], int]:
        """Распознаёт студентов на фото по сохранённым encodings.
        В простом режиме (модели не загружены) возвращает ([], 0).
        """
        self._ensure_models()
        if self._simple_mode:
            logger.warning("recognize_students вызван в простом режиме — распознавание недоступно.")
            return [], 0

        photo_encodings = self.extract_all_faces(image_bytes)
        if not photo_encodings:
            return [], 0

        student_encodings: Dict[int, np.ndarray] = {}
        for student in students:
            if student.face_encoding:
                try:
                    student_encodings[student.id] = np.array(json.loads(student.face_encoding))
                except Exception:
                    logger.warning("Некорректный face_encoding у студента id=%s", student.id)

        recognized_ids: List[int] = []
        for photo_enc in photo_encodings:
            photo_arr = np.array(photo_enc)
            best_id = None
            best_dist = float('inf')

            for student_id, student_enc in student_encodings.items():
                dist = np.linalg.norm(student_enc - photo_arr)
                if dist < best_dist and dist <= self.tolerance:
                    best_dist = dist
                    best_id = student_id

            if best_id is not None and best_id not in recognized_ids:
                recognized_ids.append(best_id)

        return recognized_ids, len(photo_encodings)

    def get_recognition_stats(
        self,
        recognized_ids: List[int],
        total_faces: int,
        total_students: int,
    ) -> Dict[str, object]:
        return {
            "recognized_count": len(recognized_ids),
            "total_faces": total_faces,
            "total_students": total_students,
            "recognition_rate": len(recognized_ids) / total_students if total_students > 0 else 0,
            "unrecognized_faces": max(0, total_faces - len(recognized_ids)),
        }
