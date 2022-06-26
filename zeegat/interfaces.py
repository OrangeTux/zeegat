from __future__ import annotations

from typing import Protocol, runtime_checkable

from zeegat.frame import Frame


@runtime_checkable
class Service(Protocol):
    """A type that turns a `Call` into something that implements :class:`IntoResponse`."""

    async def call(self, frame: Frame) -> IntoResponse:
        ...


@runtime_checkable
class IntoResponse(Protocol):
    def into_response(self) -> str:
        ...
