import asyncio
import logging

import websockets

from ocpp.v16 import call, ChargePoint as cp

logging.basicConfig(level=logging.INFO)


class Charger(cp):
    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model="Optimus", charge_point_vendor="Takara"
        )

        await self.call(request)

    async def send_firmware_status_notification(self):
        await self.call(call.FirmwareStatusNotificationPayload(status="Downloading"))

    async def send_heartbeat(self):
        await self.call(call.HeartbeatPayload())


async def calls(cp):
    await cp.send_heartbeat()
    await cp.send_boot_notification()
    await cp.send_firmware_status_notification()


async def main():

    async with websockets.connect(
        "ws://localhost:9000/optimus", subprotocols=["ocpp1.6"]
    ) as ws:
        cp = Charger("optimus", ws)

        await asyncio.gather(
            cp.start(),
            calls(cp),
        )


if __name__ == "__main__":
    asyncio.run(main())
