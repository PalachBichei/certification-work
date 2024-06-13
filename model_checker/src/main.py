from fastapi import FastAPI
from nats import connect

from handlers.nats_request_handler import NatsRequestsHandler
from handlers.reply import NatsReplyClient
from settings import get_settings
import inject

settings = get_settings()
app = FastAPI()
nats_requests_handler: NatsRequestsHandler | None = None
nats_reply_client: NatsReplyClient | None = None


def config(binder):
    global nats_requests_handler

    nats_requests_handler = NatsRequestsHandler(
        "model",
    )

    binder.bind(NatsRequestsHandler, nats_requests_handler)


@app.on_event("startup")
async def on_startup():
    global nats_reply_client
    inject.configure(config)
    nc = await connect("nats:4222", connect_timeout=20)
    nats_reply_client = NatsReplyClient(
        nc,
        "tms-orders-worker",
        nats_requests_handler,  # type: ignore
        ["subject"],
    )
    await nats_reply_client.start()


@app.on_event("shutdown")
async def on_shutdown():
    await nats_reply_client.stop()
