from __future__ import annotations

import asyncio
import functools
import sqlite3
from datetime import datetime

import websockets
from ocpp.exceptions import OCPPError

from zeegat import handler, inject, log, route, Service, timeout
from zeegat.frame import Frame
from zeegat.messages import Call, CallResult

db = sqlite3.connect(":memory:")


async def on_connect(websocket, service: Service):
    async for msg in websocket:
        frame = Frame(msg)
        try:
            response = await service.call(frame)
        except OCPPError as e:
            response = frame.as_call().create_call_error(e)

        await websocket.send(response.into_response())


def get_db(_: Frame) -> sqlite3.Cursor:
    return db.cursor()


def prepare_db(cur: sqlite3.Cursor):
    # Create table
    cur.execute("CREATE TABLE id_tags (id, name)")

    # Insert a row of data
    cur.execute("INSERT INTO id_tags VALUES ('24782', 'orangetux')")


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


async def on_heartbeat(frame: Frame) -> CallResult:
    return frame.as_call().create_call_result(
        payload={"currentTime": datetime.now().isoformat()}
    )


async def on_status_notification(call: Call) -> CallResult:
    return call.create_call_result({})


@inject(db=get_db)
async def on_authorize(call: Call, db: sqlite3.Cursor):
    id_tag = call.payload["idTag"]

    # Don't copy this query! It's vulnerable to SQL injection!
    db.execute(f"SELECT *  from id_tags WHERE id = '{id_tag}';")
    if db.rowcount == 0:
        status = "Rejected"
    else:
        status = "Accepted"

    return call.create_call_result(payload={"idTagInfo": {"status": status}})


async def main():
    # Create and populate database
    prepare_db(get_db(None))

    # Create an app that logs all requests...
    app = log(
        # ... route "Heartbeat" requests to `on_heart_beat()`.
        route("Heartbeat", handler(on_heartbeat))
        # ... route "Authorize" request to 'on_authorize'
        .route("Authorize", handler(on_authorize))
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
