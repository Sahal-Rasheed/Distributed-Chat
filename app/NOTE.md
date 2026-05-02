### WebSocket Architecture Note (Read/Write Loop + Queue Design)

Our WebSocket layer is designed using a **dual-loop (read/write) pattern with a per-connection queue** to ensure correct behavior in both single-server and distributed setups.

In the earlier approach, message sending was tightly coupled to message receiving — i.e., the server would only send messages to a client *in response to that same client sending something*. This works in a simple, single-server setup but breaks down in real-world scenarios where messages may originate from **external sources** (e.g., other servers via Redis Pub/Sub, background tasks, or system events). In such cases, the server must be able to push messages to a client even when that client is idle.

To solve this, each WebSocket connection is now backed by:

* A **read loop**: continuously listens for incoming messages from the client and processes them.
* A **write loop**: continuously listens to a per-connection **asyncio.Queue** and sends messages to the client.
* A **queue**: acts as a decoupling layer between message producers (read loop, broadcast system, Redis, etc.) and the actual network I/O (write loop).

### Why this design?

* **Decoupling of concerns**: Message production and message sending are separated.
* **Non-blocking behavior**: No network I/O (`send_json`) is performed while holding locks or inside shared critical sections.
* **Supports external events**: Messages from Redis Pub/Sub or other servers can be enqueued and delivered without requiring client interaction.
* **Scalability**: This pattern naturally extends to distributed systems where multiple servers coordinate via a message broker.
* **Backpressure handling**: Queues provide a buffer between producers and consumers, preventing slow clients from blocking the system.

### Mental Model

* Before: *"I only send messages when this client sends something."*
* Now: *"I can send messages whenever any part of the system produces one."*

This architecture is foundational for Redis Pub/Sub integration, where messages will be received independently of client actions and must still be delivered reliably to connected clients.

Each connection:

```text
Connection A:
    read_loop (A)
    write_loop (A) → listens ONLY to queue_A

Connection B:
    read_loop (B)
    write_loop (B) → listens ONLY to queue_B
```

## Managers internal Data Structure:

Inside manager:

```python
self.ws_to_queue = {
    websocket_A: queue_A,
    websocket_B: queue_B,
}
```

```python
self.active_connections = {
    "room1": [queue_A, queue_B],
    "room2": [queue_C],
}
```

## REAL flow of a message from A to B:

### Scenario

* A and B join `room1`
* A sends message: `"Hello"`

---

### Step 1 — Connections created

When A connects:

```python
queue_A = asyncio.Queue()
ws_manager.register(websocket_A, queue_A)
```

When B connects:

```python
queue_B = asyncio.Queue()
ws_manager.register(websocket_B, queue_B)
```

---

### Step 2 — Join room

A joins room1:

```python
active_connections["room1"] = [queue_A]
```

B joins room1:

```python
active_connections["room1"] = [queue_A, queue_B]
```

---

### Step 3 — A sends message

A → `read_loop`:

```python
await ws_manager.broadcast("Hello", "room1", "A")
```

---

### Step 4 — broadcast

```python
queues = [queue_A, queue_B]

for q in queues:
    await q.put({"message": "Hello", "username": "A"})
```

So now:

```text
queue_A = ["Hello"]
queue_B = ["Hello"]
```

---

### Step 5 — write loops wake up

Each connection has its own write loop:

### A’s write loop:

```python
msg = await queue_A.get()
await websocket_A.send_json(msg)
```

### B’s write loop:

```python
msg = await queue_B.get()
await websocket_B.send_json(msg)
```

---

### KEY DIFFERENCE vs old system

### Before:

```python
for websocket in room:
    await websocket.send_json(...)
```

- broadcast was directly sending

---

### Now:

```python
for queue in room:
    await queue.put(...)
```

- broadcast only *delivers messages to inboxes*

- sending is handled elsewhere (write loop)

---
