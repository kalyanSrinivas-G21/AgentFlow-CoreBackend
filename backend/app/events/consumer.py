# backend/app/events/consumer.py
import asyncio
import logging
from typing import Callable, Awaitable, List
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from app.events.envelope import EventEnvelope

logger = logging.getLogger(__name__)

class StreamConsumer:
    """
    Robust base class for consuming Redis Streams with idempotency,
    exponential backoff, and DLQ capabilities.
    """
    def __init__(
        self,
        redis_client: Redis,
        group_name: str,
        consumer_name: str,
        stream_names: List[str]
    ):
        self.redis_client = redis_client
        self.group_name = group_name
        self.consumer_name = consumer_name
        # Dictionary of streams to read from ('>' means read new messages not delivered to other consumers)
        self.streams = {stream: ">" for stream in stream_names}
        self.max_attempts = 4
        self.visibility_timeout_ms = 30000  # 30 seconds
        self._running = False

    async def initialize(self) -> None:
        """Ensure consumer groups exist idempotently."""
        for stream in self.streams.keys():
            try:
                # Fixed: Added id="0" to start reading from the beginning of the stream,
                # preventing missed messages if the stream was populated before initialization.
                await self.redis_client.xgroup_create(stream, self.group_name, id="0", mkstream=True)
            except ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

    async def _check_idempotency(self, key: str) -> bool:
        """
        Uses SETNX to enforce idempotency. Returns True if execution is allowed.
        Processed keys have a 24-hour TTL.
        """
        is_new = await self.redis_client.setnx(f"processed:{key}", "1")
        if is_new:
            await self.redis_client.expire(f"processed:{key}", 86400)
            return True
        return False

    async def _handle_dlq(self, stream_name: str, message_id: str, payload: dict) -> None:
        """Moves a message to the DLQ after max attempts and XACKs the original."""
        prefix = stream_name.split(":")[1]
        dlq_stream = f"stream:{prefix}.deadletter"
        
        await self.redis_client.xadd(dlq_stream, payload)
        await self.redis_client.xack(stream_name, self.group_name, message_id)
        logger.warning(f"Message {message_id} routed to DLQ {dlq_stream}.")

    async def _reap_stale_messages(self) -> None:
        """Background task to XCLAIM pending messages and handle DLQ routing."""
        while self._running:
            try:
                for stream_name in self.streams.keys():
                    pending_info = await self.redis_client.xpending_range(
                        stream_name, self.group_name, "-", "+", 100
                    )
                    
                    for msg_info in pending_info:
                        message_id = msg_info["message_id"]
                        idle_time = msg_info["time_since_delivered"]
                        
                        if idle_time > self.visibility_timeout_ms:
                            claimed = await self.redis_client.xclaim(
                                stream_name,
                                self.group_name,
                                self.consumer_name,
                                self.visibility_timeout_ms,
                                [message_id]
                            )
                            
                            if claimed:
                                msg = claimed[0]
                                payload = msg[1]
                                attempt_key = f"attempts:{message_id}"
                                attempts = await self.redis_client.hincrby(attempt_key, "count", 1)
                                
                                if attempts >= self.max_attempts:
                                    await self._handle_dlq(stream_name, message_id, payload)
                                    await self.redis_client.delete(attempt_key)
            except Exception as e:
                logger.error(f"Error in reaper task: {e}")
            
            await asyncio.sleep(10)

    async def consume(self, handler: Callable[[EventEnvelope], Awaitable[None]]) -> None:
        """Main consumption loop."""
        self._running = True
        asyncio.create_task(self._reap_stale_messages())
        
        while self._running:
            try:
                results = await self.redis_client.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    self.streams,
                    count=10,
                    block=2000
                )
                
                for stream_name, messages in results:
                    stream_name = stream_name.decode("utf-8") if isinstance(stream_name, bytes) else stream_name
                    
                    for message_id, payload_raw in messages:
                        message_id = message_id.decode("utf-8") if isinstance(message_id, bytes) else message_id
                        payload = {
                            (k.decode("utf-8") if isinstance(k, bytes) else k): 
                            (v.decode("utf-8") if isinstance(v, bytes) else v)
                            for k, v in payload_raw.items()
                        }
                        
                        envelope_json = payload.get("envelope")
                        envelope = EventEnvelope.model_validate_json(envelope_json)
                        
                        idempotency_key = envelope.idempotency_key
                        if await self._check_idempotency(idempotency_key):
                            try:
                                await handler(envelope)
                                await self.redis_client.xack(stream_name, self.group_name, message_id)
                                await self.redis_client.delete(f"attempts:{message_id}")
                            except Exception as e:
                                logger.error(f"Error processing {message_id}: {e}")
                                await self.redis_client.delete(f"processed:{idempotency_key}")
                        else:
                            await self.redis_client.xack(stream_name, self.group_name, message_id)

            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False