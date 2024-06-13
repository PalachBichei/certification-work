from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID

import dacite
import orjson
from mashumaro import DataClassDictMixin
from mashumaro.mixins.json import DataClassJSONMixin

TYPES_MAPPING = {UUID: str}


def to_nats(data):
    def _format_dict(obj):
        new_obj = {}
        for k, v in obj.items():
            if isinstance(v, dict):
                value = _format_dict(v)
            else:
                value = _format_value(v)
            new_obj[_format_value(k)] = value
        return new_obj

    def _format_value(obj):
        if type(obj) in TYPES_MAPPING:
            return TYPES_MAPPING[type(obj)](obj)
        return obj

    if isinstance(data, dict):
        return _format_dict(data)
    return _format_value(data)


@runtime_checkable
@dataclass
class DataclassProtocol(Protocol):
    pass


@dataclass
class NatsMessage(DataClassJSONMixin, DataClassDictMixin):
    ts: datetime
    type: str
    data: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)
    specversion: str = "2.0"
    source_meta: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def build(
        message_type: str,
        message_payload: DataclassProtocol | dict,
        meta: dict | None = None,
    ) -> "NatsMessage":
        if is_dataclass(message_payload):
            data = to_nats(asdict(message_payload))  # type: ignore
        else:
            data = message_payload

        return NatsMessage(ts=datetime.now(), type=message_type, data=data, meta=meta or {})

    @property
    def num_delivered(self) -> int:
        num_delivered = self.source_meta.get("num_delivered")
        if not num_delivered:
            raise RuntimeError("Nats message source meta is undefined")
        return num_delivered


class NatsMessageHandlerProtocol(Protocol):
    async def handle(self, subject: str, message: NatsMessage) -> None | NatsMessage:
        ...


@dataclass
class NatsError:
    text: str
    data: dict | None


T = TypeVar("T")


@dataclass
class NatsReply(Generic[T]):
    data: T
    error: NatsError | None
    message: NatsMessage

    @staticmethod
    def build(message: NatsMessage, data_cls=None) -> "NatsReply":
        data: Any = None
        error: NatsError | None = None
        msg_error = message.data.get("error")
        if isinstance(msg_error, dict):
            error = NatsError(text=msg_error.get("text", ""), data=msg_error.get("data"))
        else:
            data = message.data.get("data") if "data" in message.data else message.data
            if data_cls is not None and data_cls is not dict:
                data = dacite.from_dict(data_class=data_cls, data=data)
            if data_cls is dict and isinstance(data, str):
                data = orjson.loads(data)

        return NatsReply(data=data, error=error, message=message)


# deprecated format
@dataclass
class EventMessageV1(DataClassJSONMixin, DataClassDictMixin):
    event_timestamp: datetime
    subject: Enum | str
    event_type: Enum | str
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    specversion: str = "1.0"

    class Meta:
        json_module = orjson

    @staticmethod
    def build(
        backward_subject: str,
        message_type: str,
        message_payload: DataclassProtocol | dict,
        meta: dict | None = None,
    ) -> "EventMessageV1":
        if is_dataclass(message_payload):
            data = to_nats(asdict(message_payload))  # type: ignore
        else:
            data = message_payload

        return EventMessageV1(  # type: ignore
            event_timestamp=datetime.now(),
            subject=backward_subject,
            event_type=message_type,
            data=data,
            metadata=meta or {},
        )
