from typing import Optional

import inject
import nats
from nats import NATS

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from handlers.request import NatsApi
from handlers.request_client import NatsRequestClient
from services.service import FileService
from router import router as file_router
from settings import get_settings

settings = get_settings()

app = FastAPI()
app.include_router(file_router)

nc: Optional[NATS] = None

def config(binder):
    nats_requests_client = NatsRequestClient("backend", nc)
    binder.bind(NatsRequestClient, nats_requests_client)

    nats_api = NatsApi(nats_requests_client)
    binder.bind(NatsApi, nats_api)

    file_service = FileService(nats_api)
    binder.bind(FileService, file_service)

@app.on_event("startup")
async def on_startup():
    global nc
    nc = await nats.connect("nats:4222", connect_timeout=20)
    inject.configure(config)



@app.on_event("shutdown")
async def on_shutdown():
    pass


origins = [
    "http://localhost:63342",
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
