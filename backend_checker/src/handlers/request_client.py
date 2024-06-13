import asyncio
import time
from typing import Any, Type

import nats.errors
import orjson
from nats.aio.client import Client as NatsAioClient
from nats.aio.subscription import Subscription

from handlers.message import (
    DataclassProtocol,
    EventMessageV1,
    NatsMessage,
    NatsReply,
)

encoder = orjson.dumps
decoder = orjson.loads


class NatsRequestClient:
    def __init__(self, service_name: str, nc: NatsAioClient) -> None:
        self._nc = nc
        self.service_name = service_name
        self.meta = {"src": self.service_name}

    async def request(
        self,
        subject: str,
        message_type: str,
        message_payload: DataclassProtocol | dict,
        reply_model: Type[Any] | None = None,
        timeout: int = 5,
        timeout_per_message: float = 5.0,
    ) -> NatsReply:
        replies = await self.requests(
            subject,
            message_type,
            message_payload,
            reply_model,
            replies_count=1,
            timeout=timeout,
            timeout_per_message=timeout_per_message,
        )
        return replies[0]

    async def requests(
        self,
        subject: str,
        message_type: str,
        message_payload: DataclassProtocol | dict,
        reply_model: Type[Any] | None = None,
        replies_count: int = 2,
        timeout: int = 5,
        timeout_per_message: float = 5.0,
    ) -> list[NatsReply]:
        message = NatsMessage.build(message_type, message_payload, self.meta)
        replies = await self.requests_core(
            subject, message, replies_count, timeout, timeout_per_message
        )
        return [NatsReply.build(reply, reply_model) for reply in replies]

    async def requests_core(
        self,
        subject: str,
        message: NatsMessage | EventMessageV1,
        replies_count: int = 0,
        timeout: int = 5,
        timeout_per_message: float = 5.0,
    ) -> list[NatsMessage]:
        start_ts = time.time()
        message_type = str(
            (message.type if isinstance(message, NatsMessage) else message.event_type)
        )
        print(
            f"[{start_ts}] --> NATS request sending {subject}#{message_type} {message.data}"
        )

        payload: bytes = message.to_json(encoder=encoder)  # type: ignore
        replies = []
        try:
            if replies_count > 0:
                inbox = self._nc.new_inbox()
                sub = await self._nc.subscribe(inbox, max_msgs=replies_count)
                try:
                    await self._nc.publish(subject, payload, reply=inbox)
                    replies = await asyncio.wait_for(
                        self._wait_replies(
                            sub, message_type, replies_count, timeout_per_message
                        ),
                        timeout,
                    )
                finally:
                    await sub.unsubscribe()
            else:
                await self._nc.publish(subject, payload)
            return replies
        finally:
            duration = time.time() - start_ts
            if replies:
                print(f"[{start_ts}] --> NATS reply received ({duration:.3f}s) {subject}#{message_type} {str(replies)}")
            else:
                print(f"[{start_ts}] --> ZERO NATS reply received ({duration:.3f}s) {subject}#{message_type}")

    async def _wait_replies(
        self,
        sub: Subscription,
        message_type: str,
        replies_count: int,
        timeout_per_message: float,
    ) -> list[NatsMessage]:
        replies: list[NatsMessage] = []
        try:
            while len(replies) != replies_count:
                msg = await sub.next_msg(timeout=timeout_per_message)
                if msg and msg.data:
                    data_json = orjson.loads(msg.data)
                    specversion = data_json.get("specversion")
                    if specversion == "1.0":
                        deprecated_msg = EventMessageV1.from_dict(data_json)
                        replies.append(
                            NatsMessage(
                                ts=deprecated_msg.event_timestamp,
                                type=str(deprecated_msg.event_type),
                                data=deprecated_msg.data,
                            )
                        )
                    else:
                        replies.append(NatsMessage.from_json(msg.data, decoder=decoder))
        except nats.errors.TimeoutError:
            print(
                f"nats.errors.TimeoutError while waiting for reply to {message_type}"
            )
        except Exception as ex:
            print(
                f"Exception while waiting for reply to {message_type}: {ex}"
            )

        return replies