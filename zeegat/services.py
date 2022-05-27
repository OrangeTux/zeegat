import asyncio
import logging
from typing import Dict

from ocpp.exceptions import InternalError, NotSupportedError, OCPPError

from zeegat.interfaces import Handler, IntoResponse, Service
from zeegat.messages import Call


logging.basicConfig(level=logging.INFO)
l = logging.getLogger(__name__)


class log:
    """A :class:`Service` that logs request and responses to stdout."""

    def __init__(self, service: Service):
        self._service = service

    async def call(self, request: Call) -> IntoResponse:
        response = await self._service.call(request)
        l.info("%s - %s", request, response)
        return response


class timeout:
    """A :class:`Service` that returns a :class:`CallError` containing
    InternalError if inner service doesn't respond in time.

    """

    def __init__(self, interval_in_s: int, service: Service):
        self._interval = interval_in_s
        self._service = service

    async def call(self, request: Call) -> IntoResponse:
        try:
            future = await asyncio.wait_for(self._service.call(request), self._interval)
        except asyncio.TimeoutError:
            raise InternalError(
                details={"cause": f"Handler for action {request.action} timed out."}
            )

        return await future


class route:
    """A :class:`Service` that routes requests to :class:`Handler`s."""

    def __init__(self, action: str, service: Handler | Service):
        self._routes: Dict[str, Service] = {}
        self.route(action, service)

    def route(self, action: str, service: Handler | Service):
        if action in self._routes:
            raise Exception(
                f"Can't register handler for action {action}: already a handler registered."
            )

        if not isinstance(service, Service):
            service = handler(service)

        self._routes[action] = service
        return self

    async def call(self, call: Call) -> IntoResponse:
        try:
            try:
                service = self._routes[call.action]
            except KeyError:
                raise NotSupportedError(
                    details={"cause": f"No handler for {call.action} registered."}
                )
            else:
                return await service.call(call)
        except OCPPError as e:
            return call.create_call_error(e)


class handler:
    """A :class:`Service` wrapping a :class:`Handler` as a :class:`Service`."""

    def __init__(self, handler: Handler):
        self._handler = handler

    async def call(self, call: Call) -> IntoResponse:
        return await self._handler(call)
