from handlers.message import DataclassProtocol, NatsMessage
from nats.aio.client import Client as NatsAioClient


class NatsPublisher:
    def __init__(self, service_name: str, nc: NatsAioClient) -> None:
        self._js = nc.jetstream()
        self.service_name = service_name
        self.meta = {"src": self.service_name}

    async def publish(
        self, subject: str, message_type: str, message_payload: DataclassProtocol | dict
    ):
        message = NatsMessage.build(message_type, message_payload, self.meta)
        await self.publish_js(subject, message)
        (
            f"Nats published: {subject}#{message_type} payload {message_payload}"
        )

    async def publish_js(self, subject: str, message: NatsMessage) -> None:
        payload: bytes = message.to_json(encoder=encoder)  # type: ignore
        await self._js.publish(subject, payload)