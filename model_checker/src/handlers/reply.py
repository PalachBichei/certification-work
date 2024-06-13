import logging

import orjson
from nats.aio.client import Client as NatsAioClient
from nats.aio.msg import Msg
from nats.aio.subscription import Subscription

from handlers.message import NatsMessageHandlerProtocol, EventMessageV1, NatsMessage

logger = logging.getLogger("handlers")

encoder = orjson.dumps
decoder = orjson.loads


class NatsReplyClient:
    def __init__(
            self,
            nc: NatsAioClient,
            queue_group: str,
            handler: NatsMessageHandlerProtocol,
            subjects: list[str],
    ) -> None:
        self._nc = nc
        self.queue_group = queue_group
        self._handler = handler
        self._subjects = subjects
        self._subscriptions: list[Subscription] = []

    async def start(self):
        for subject in self._subjects:
            logger.info(
                f"Starting NATS request-reply subscription with queue-group {self.queue_group} for subject [{subject}]"
            )
            sub = await self._nc.subscribe(subject=subject, queue=self.queue_group, cb=self.on_request)
            self._subscriptions.append(sub)

    async def stop(self):
        for sub in self._subscriptions:
            await sub.unsubscribe()
        self._subscriptions.clear()

    async def on_request(self, msg: Msg) -> None:
        data_json = orjson.loads(msg.data)
        specversion = data_json.get("specversion")
        if specversion == "1.0":
            deprecated_msg = EventMessageV1.from_dict(data_json)
            message = NatsMessage(
                ts=deprecated_msg.event_timestamp,
                type=str(deprecated_msg.event_type),
                data=deprecated_msg.data,
            )
        else:
            message = NatsMessage.from_json(msg.data, decoder=decoder)

        reply = await self._handler.handle(msg.subject, message)
        if reply is not None:
            if specversion == "1.0":
                reply_msg = EventMessageV1(
                    event_timestamp=reply.ts,
                    event_type=reply.type,
                    subject=msg.subject,
                    data=reply.data,
                )
                await msg.respond(reply_msg.to_json(encoder=encoder))  # type: ignore
            else:
                await msg.respond(reply.to_json(encoder=encoder))  # type: ignore
