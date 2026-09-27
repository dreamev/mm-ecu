"""Outbound CAN frame queue."""

FRAME_LENGTH = 8


def frame_data(data):
    """Pad with zeros or truncate to a full 8-byte CAN payload."""
    data = bytes(data[:FRAME_LENGTH])
    return data + bytes(FRAME_LENGTH - len(data))


class Outbox:
    """FIFO of (can_id, payload) frames, drained one per main-loop tick."""

    def __init__(self):
        self._frames = []

    def __len__(self):
        return len(self._frames)

    def push(self, can_id, data):
        self._frames.append((can_id, frame_data(data)))

    def pop(self):
        return self._frames.pop(0) if self._frames else None
