from zeegat.messages import Call, unpack


class Frame:
    def __init__(self, frame: bytes):
        self._frame = frame

    def as_call(self) -> Call:
        return unpack(self._frame)

    def as_bytes(self) -> bytes:
        return self._frame

    @staticmethod
    def from_frame(frame):
        return frame
