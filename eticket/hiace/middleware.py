from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.tokens import AccessToken

from eticketauth.models import User


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        # Example:
        # ws://127.0.0.1:8000/ws/trips/25/seats/?token=xxxxx

        query_string = scope.get(
            "query_string",
            b"",
        ).decode()

        query_params = parse_qs(query_string)

        token = query_params.get(
            "token",
            [None],
        )[0]

        if not token:
            scope["user"] = AnonymousUser()

            return await super().__call__(
                scope,
                receive,
                send,
            )

        try:
            access_token = AccessToken(token)

            user_id = access_token["user_id"]

            scope["user"] = await get_user(user_id)

        except Exception as e:

            print(
                "WebSocket JWT authentication error:",
                str(e),
            )

            scope["user"] = AnonymousUser()

        return await super().__call__(
            scope,
            receive,
            send,
        )
