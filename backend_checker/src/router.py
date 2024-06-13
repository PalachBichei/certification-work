import asyncio

from fastapi import APIRouter, UploadFile, Depends

router = APIRouter(tags=["Files"],)
from services import FileService, get_file_service


@router.post("/upload")
async def upload_file(
        file: UploadFile,
        service: FileService = Depends(get_file_service)
):
    result = await service.check_violation(file)
    return result
