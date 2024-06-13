import asyncio
import base64
from typing import Type, Any

from asyncio.tasks import FIRST_COMPLETED

from fastapi import UploadFile

from handlers.message import DataclassProtocol, NatsReply, EventMessageV1, NatsMessage
from handlers.request_client import NatsRequestClient


class NatsApiBase:
    def __init__(self, nats: NatsRequestClient) -> None:
        self.nats = nats

    async def requests(
        self,
        subject: str,
        message_type: str,
        message_payload: DataclassProtocol | dict,
        reply_model: Type[Any] | None = None,
        timeout: int = 5,
        timeout_per_message: float = 5.0,
        replies_count: int = 2,
        backward_subject: str | None = None,
    ) -> list[NatsReply]:
        # make 2 requests for backward compatibility
        # TODO: remove request to NATS_REQUEST_REPLY_SUBJECT

        task = self.nats.requests(
            subject,
            message_type,
            message_payload,
            reply_model,
            replies_count,
            timeout,
            timeout_per_message,
        )
        tasks = [asyncio.create_task(task)]
        if backward_subject:
            backward_task = self.nats.requests_core(
                subject="subject",
                message=EventMessageV1.build(backward_subject, message_type, message_payload),
                replies_count=replies_count,
                timeout=timeout,
                timeout_per_message=timeout_per_message,
            )
            tasks.append(asyncio.create_task(backward_task))  # type: ignore
        finished_tasks, unfinished_tasks = await asyncio.wait(tasks, timeout=timeout, return_when=FIRST_COMPLETED)
        for unfinished_task in unfinished_tasks:
            unfinished_task.cancel()
        replies: list[NatsReply] = []
        for finished_task in finished_tasks:
            replies.extend(finished_task.result())  # type: ignore
        return replies

    async def request(
        self,
        subject: str,
        message_type: str,
        message_payload: DataclassProtocol | dict,
        timeout: int = 5,
        timeout_per_message: float = 5.0,
        reply_model: Type[Any] | None = None,
        backward_subject: str | None = None,
    ) -> NatsReply:
        # make 2 requests for backward compatibility
        # TODO: remove request to NATS_REQUEST_REPLY_SUBJECT

        task = self.nats.request(
            subject,
            message_type,
            message_payload,
            reply_model,
            timeout,
            timeout_per_message,
        )
        tasks = [asyncio.create_task(task)]
        if backward_subject:
            backward_task = self.nats.requests_core(
                subject="subject",
                message=EventMessageV1.build(backward_subject, message_type, message_payload),
                replies_count=1,
                timeout=timeout,
                timeout_per_message=timeout_per_message,
            )
            tasks.append(asyncio.create_task(backward_task))  # type: ignore
        finished_tasks, unfinished_tasks = await asyncio.wait(tasks, timeout=timeout, return_when=FIRST_COMPLETED)
        for unfinished_task in unfinished_tasks:
            unfinished_task.cancel()

        replies: list[NatsReply] = []
        for finished_task in finished_tasks:
            res = finished_task.result()
            reply = res[0] if isinstance(res, list) else res
            if isinstance(reply, NatsMessage):
                replies.append(NatsReply.build(reply, reply_model))
            else:
                replies.append(reply)  # type: ignore

        return replies[0]


class ModelApi(NatsApiBase):
    subject = "subject"

    async def is_violation(self, file: UploadFile):
        file_bytes = await file.read()

        file_base64 = base64.b64encode(file_bytes).decode()

        payload = dict(
            filename=file.filename,
            file=file_base64,
            size=file.size,
        )
        reply = await self.request(self.subject, "check_violation", payload, reply_model=dict)
        return reply.data


class NatsApi:
    def __init__(self, nats_requests: NatsRequestClient):
        self.model = ModelApi(nats_requests)
