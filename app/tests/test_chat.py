import pytest
from fastapi.testclient import TestClient


def test_chat_websocket(client: TestClient):
    """
    A test that opens three connections A, B, C.
    Join A and B to room1, C to room2. A sends a message to room1.
    Assert B received it. Assert C did not.
    """
    with (
        client.websocket_connect("/ws/chat") as ws_a,
        client.websocket_connect("/ws/chat") as ws_b,
        client.websocket_connect("/ws/chat") as ws_c,
    ):
        # join rooms
        ws_a.send_json({"type": "join_room", "username": "UserA", "room": "room1"})
        ws_b.send_json({"type": "join_room", "username": "UserB", "room": "room1"})
        ws_c.send_json({"type": "join_room", "username": "UserC", "room": "room2"})

        # consume join room responses
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        # user A sends a message to room1
        test_message = {
            "type": "chat_message",
            "username": "UserA",
            "room": "room1",
            "content": "Hello Room1!",
        }
        ws_a.send_json(test_message)

        # assert B (in room1) received it
        received_b = ws_b.receive_json()
        assert received_b["message"] == test_message["content"]

        # assert C (in room2) did NOT receive it
        # we expect this to time out because no message should arrive
        # if we use `receive_json` without timeout, it will block indefinitely,
        # so we set a short timeout to assert that no message is received.

        with pytest.raises(Exception):
            ws_c.receive_json(timeout=1)
