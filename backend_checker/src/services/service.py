import inject
from fastapi import UploadFile

from handlers.request import NatsApi

service = None

@inject.autoparams()
def get_service():
    global service
    if service is None:
        service = FileService()
    return service


class FileService:

    @inject.autoparams()
    def __init__(
            self,
            nats_api: NatsApi,
    ):
        self.nats_api = nats_api

    async def check_violation(self, file: UploadFile):
        self._validate_file(file)
        return await self.nats_api.model.is_violation(file)

    @staticmethod
    def _validate_file(file: UploadFile):
        if file.size > 8 * 1024 * 1024:  # MB
            raise ValueError("Файл слишком большой")
        if len(file.filename) > 255:
            raise ValueError("Слишком длинное название")


