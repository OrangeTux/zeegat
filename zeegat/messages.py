from __future__ import annotations

import json

from ocpp import messages
from ocpp.exceptions import OCPPError


def unpack(msg) -> Call:
    """
    Unpacks a message into either a Call.
    """
    msg = json.loads(msg)

    if msg[0] == Call.message_type_id:
        return Call(*msg[1:])

    raise Exception(
        f"Received unsupported message type {msg[0]}. Project only supports receiving Calls as of now. "
    )


class Call(messages.Call):
    @staticmethod
    def from_frame(frame) -> Call:
        return frame.as_call()

    def into_response(self) -> str:
        return self.to_json()

    def create_call_result(self, payload) -> CallResult:
        return CallResult(self.unique_id, payload)

    def create_call_error(self, exception):
        error_code = "InternalError"
        error_description = "An unexpected error occurred."
        error_details = {}

        if isinstance(exception, OCPPError):
            error_code = exception.code
            error_description = exception.description
            error_details = exception.details

        return CallError(
            self.unique_id,
            error_code,
            error_description,
            error_details,
        )


class CallResult(messages.CallResult):
    def into_response(self) -> str:
        return self.to_json()


class CallError(messages.CallError):
    def into_response(self) -> str:
        return self.to_json()
