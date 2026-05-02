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
