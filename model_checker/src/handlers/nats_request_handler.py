import base64
from typing import Any, Callable

import orjson

from keras.models import load_model
from PIL import Image, ImageOps
import numpy as np
import io

from handlers.handler import NatsMessageHandler
from handlers.message import NatsMessage
class NatsRequestsHandler(NatsMessageHandler):
    def __init__(
            self,
            service_name: str,
    ) -> None:
        super().__init__(service_name)

        self._handlers: dict[str, Callable[[NatsMessage], Any]] = {
            "check_violation": self.check_violation,
        }

    def get_handler(self, subject: str, message_type: str) -> \
            Callable[[NatsMessage], Any] | None:
        return self._handlers.get(message_type)

    async def check_violation(self, event: NatsMessage):
        model = load_model("keras_model.h5", compile=False)
        class_names = open("labels.txt", "r").readlines()

        file = base64.b64decode(event.data["file"])
        image = Image.open(io.BytesIO(file)).convert("RGB")

        size = (224, 224)
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

        image_array = np.asarray(image)
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1

        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data[0] = normalized_image_array

        prediction = model.predict(data)
        index = np.argmax(prediction)
        class_name = class_names[index]
        confidence_score = prediction[0][index]

        result = {
            'class_name': class_name[2:],
            'confidence_score': float(confidence_score)
        }
        return result
