# hiace/consumers.py

import json
import redis
import asyncio
from concurrent.futures import ThreadPoolExecutor
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=10)

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    socket_keepalive=True,
    health_check_interval=30,
    max_connections=10,
)


def hiace_seat_key(trip_id, seat_id):
    return f"hiace_trip:{trip_id}:seat:{seat_id}:selected"


class HiaceSeatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        try:
            user = self.scope.get("user")

            if not user or user.is_anonymous:
                logger.warning("Hiace WebSocket rejected: user is not authenticated")
                await self.close(code=4001)
                return

            self.user = user
            self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
            self.group_name = f"hiace_trip_seats_{self.trip_id}"

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )

            await self.accept()

            logger.info(
                f"Hiace WebSocket connected: user={self.user.id}, trip={self.trip_id}"
            )

            selected_seats = await self.get_selected_seats_async()

            await self.send_json({
                "type": "initial_seats",
                "seats": selected_seats,
            })

        except Exception as e:
            logger.error(f"Hiace WebSocket connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "group_name"):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name,
                )
            logger.info(
                f"Hiace WebSocket disconnected: "
                f"user={getattr(self.user, 'id', None)}, "
                f"trip={getattr(self, 'trip_id', None)}, code={close_code}"
            )
        except Exception as e:
            logger.error(f"Hiace disconnect error: {e}")

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        if message_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if message_type == "select_seat":
            await self.send_json({
                "type": "use_api",
                "message": "Use SelectSeatView API to select the seat.",
                "seat_id": content.get("seat_id"),
            })
            return

        if message_type == "release_seat":
            await self.send_json({
                "type": "use_api",
                "message": "Use ReleaseSeatView API to release the seat.",
                "seat_id": content.get("seat_id"),
            })
            return

        await self.send_json({
            "type": "error",
            "message": "Unknown WebSocket message type",
        })

    async def seat_selected(self, event):
        await self.send_json({
            "type": "seat_selected",
            "seat_id": event["seat_id"],
            "user_id": event["user_id"],
            "username": event.get("username"),
        })

    async def seat_available(self, event):
        await self.send_json({
            "type": "seat_available",
            "seat_id": event["seat_id"],
        })

    async def get_selected_seats_async(self):
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                executor,
                self._get_selected_seats_sync
            )
        except Exception as e:
            logger.error(f"Error getting hiace selected seats: {e}")
            return []

    def _get_selected_seats_sync(self):
        try:
            pattern = f"hiace_trip:{self.trip_id}:seat:*:selected"
            seats = []

            local_redis = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )

            for key in local_redis.scan_iter(match=pattern, count=100):
                try:
                    value = local_redis.get(key)
                    if not value:
                        continue

                    data = json.loads(value)
                    parts = key.split(":")

                    if len(parts) < 5:
                        continue

                    seat_id = parts[3]
                    ttl = local_redis.ttl(key)

                    seats.append({
                        "seat_id": seat_id,
                        "user_id": data.get("user_id"),
                        "name": data.get("name"),
                        "is_mine": data.get("user_id") == self.user.id,
                        "ttl": ttl if ttl > 0 else 600,
                    })
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.error(f"Error processing hiace seat {key}: {e}")
                    continue

            local_redis.close()
            return seats

        except Exception as e:
            logger.error(f"Unexpected error in hiace get_selected_seats: {e}")
            return []