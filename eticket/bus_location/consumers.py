from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BusLocationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        self.bus_id = self.scope["url_route"]["kwargs"]["bus_id"]

        self.group_name = f"bus_location_{self.bus_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send_json(
            {
                "type": "connection",
                "message": "Bus location connected",
                "bus_id": self.bus_id,
            }
        )

    async def disconnect(self, close_code):

        if hasattr(self, "group_name"):

            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):

        message_type = content.get("type")

        if message_type == "ping":

            await self.send_json(
                {
                    "type": "pong",
                }
            )

    async def bus_location_update(self, event):

        await self.send_json(
            {
                "type": "bus_location",
                "data": event["data"],
            }
        )