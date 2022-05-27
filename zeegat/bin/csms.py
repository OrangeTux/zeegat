from __future__ import annotations

import asyncio
import functools
from datetime import datetime

import websockets
from ocpp.exceptions import OCPPError

from zeegat import handler, log, route, Service, timeout
from zeegat.messages import Call, CallResult, unpack


async def on_connect(websocket, service: Service):
    async for msg in websocket:
        call = unpack(msg)
        try:
            response = await service.call(call)
        except OCPPError as e:
            response = call.create_call_error(e)

        await websocket.send(response.into_response())


class CSMS:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    @staticmethod
    def bind(host: str, port: int) -> CSMS:
        return CSMS(host, port)

    async def serve(self, service: Service):
        async with websockets.serve(
            functools.partial(on_connect, service=service), self._host, self._port
        ):
            await asyncio.Future()


async def on_heartbeat(call: Call) -> CallResult:
    return call.create_call_result(payload={"currentTime": datetime.now().isoformat()})


async def on_status_notification(call: Call) -> CallResult:
    await asyncio.sleep(2)
    return call.create_call_result({})


async def main():

    # Log all requests...
    app = log(
        # ... route "Heartbeat" requests to handler `on_heart_beat()`.
        route("Heartbeat", on_heartbeat)
        # ... route "FirmwareStatusNotification" to `on_status_notification()`.
        # that times out after 1 second.
        .route(
            "FirmwareStatusNotification",
            # ...
            timeout(interval_in_s=1, service=handler(on_status_notification)),
        )
    )

    await CSMS.bind("localhost", 9000).serve(app)


if __name__ == "__main__":
    asyncio.run(main())
