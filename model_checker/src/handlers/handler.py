import time
from typing import Any, Awaitable, Callable

import orjson

from handlers.message import NatsMessageHandlerProtocol, NatsMessage, DataclassProtocol

encoder = orjson.dumps
decoder = orjson.loads


class NatsMessageHandler(NatsMessageHandlerProtocol):
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.meta = {"src": self.service_name}

    async def handle(self, subject: str, message: NatsMessage) -> None | NatsMessage:
        msg_handler = self.get_handler(subject, message.type)
        if msg_handler is None:
            print(f"<-- NO HANDLER for NATS msg {subject}#{message.type}")
            return None

        return await self.process_message(subject, message, msg_handler)

    async def process_message(
            self,
            subject: str,
            message: NatsMessage,
            handler: Callable[[NatsMessage], Awaitable[DataclassProtocol | dict]],
    ) -> Any | None:
        start_ts = time.time()
        print(
            f"<-- NATS msg received {subject}#{message.type} "
            f"(src: {message.meta.get('src')}) {message.data}"
        )

        reply: NatsMessage | None = None
        try:
            result = await handler(message)
            if result is not None:
                reply = NatsMessage.build(f"REPLY_{message.type}", result, self.meta)
            return reply
        finally:
            duration = time.time() - start_ts
            dst = f"(dst: {reply.meta.get('dst')})" if reply and reply.meta else ""
            print(
                f"<-- NATS msg handled ({duration:.3f}s) {subject}#{message.type} {dst} {reply}"
            )

    def get_handler(
            self, subject: str, message_type: str
    ) -> Callable[[NatsMessage], Awaitable[DataclassProtocol | dict]] | None:
        raise NotImplementedError
