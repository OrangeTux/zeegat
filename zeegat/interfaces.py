from __future__ import annotations

from typing import Awaitable, Callable, Protocol, runtime_checkable

from zeegat.messages import Call


@runtime_checkable
class Service(Protocol):
    """A type that turns a `Call` into something that implements :class:`IntoResponse`."""

    async def call(self, request: Call) -> IntoResponse:
        ...


@runtime_checkable
class IntoResponse(Protocol):
    def into_response(self) -> str:
        ...


# A coroutine matching the signature `async def handler(call: Call) -> IntoResponse`.
Handler = Callable[[Call], Awaitable[IntoResponse]]
