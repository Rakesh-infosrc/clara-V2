"""Microsoft Teams messaging utilities using Microsoft Graph."""

import asyncio
import json
import logging
from typing import Optional

import httpx

from .config import (
    get_graph_client_id,
    get_graph_client_secret,
    get_graph_tenant_id,
    get_graph_app_display_name,
    get_graph_app_object_id,
)


class GraphAuthError(RuntimeError):
    """Raised when Microsoft Graph authentication fails."""


class GraphSendError(RuntimeError):
    """Raised when sending a Teams message via Microsoft Graph fails."""


class GraphClient:
    TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    SCOPE = "https://graph.microsoft.com/.default"

    def __init__(self, *, client_id: str, client_secret: str, tenant_id: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        self._access_token: Optional[str] = None

    async def _fetch_token(self) -> str:
        token_url = self.TOKEN_URL_TEMPLATE.format(tenant_id=self._tenant_id)
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self.SCOPE,
            "grant_type": "client_credentials",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise GraphAuthError(
                f"Failed to acquire Graph token ({response.status_code}): {response.text}"
            )
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise GraphAuthError("Graph token response missing access_token")
        self._access_token = token
        return token


    async def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        return await self._fetch_token()

    @property
    def headers(self) -> dict[str, str]:
        if not self._access_token:
            raise GraphAuthError("Access token not acquired yet")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }


logger = logging.getLogger("teams_sender")


async def _ensure_client() -> GraphClient:
    client_id = get_graph_client_id()
    client_secret = get_graph_client_secret()
    tenant_id = get_graph_tenant_id()
    if not client_id or not client_secret or not tenant_id:
        raise GraphAuthError(
            "Microsoft Graph credentials missing. Define GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, and GRAPH_TENANT_ID."
        )
    return GraphClient(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)


async def _resolve_user_id(http_client: httpx.AsyncClient, user_principal_name: str) -> str:
    response = await http_client.get(
        "https://graph.microsoft.com/v1.0/users",
        params={"$filter": f"userPrincipalName eq '{user_principal_name}'"},
    )
    if response.status_code != 200:
        raise GraphSendError(
            f"Failed to resolve user '{user_principal_name}' ({response.status_code}): {response.text}"
        )
    data = response.json()
    value = data.get("value", [])
    if not value:
        raise GraphSendError(f"No Azure AD user found for '{user_principal_name}'")
    return value[0]["id"]


async def send_teams_message(
    *,
    user_principal_name: str,
    message: str,
    subject: Optional[str] = None,
) -> str:
    client = await _ensure_client()
    token = await client.get_access_token()
    app_display_name = get_graph_app_display_name()
    app_object_id = get_graph_app_object_id()
    if not app_object_id:
        raise GraphSendError(
            "GRAPH_APP_OBJECT_ID not configured; cannot join app to Teams chat."
        )
    logger.debug(
        "Sending Teams message",
        extra={
            "user": user_principal_name,
            "subject": subject,
            "app": app_display_name,
        },
    )

    async with httpx.AsyncClient(timeout=30.0, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }) as http_client:
        user_id = await _resolve_user_id(http_client, user_principal_name)
        logger.debug(
            "Resolved Teams user",
            extra={"user": user_principal_name, "user_id": user_id},
        )

        chat_body = {
            "chatType": "oneOnOne",
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
                },
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/directoryObjects('{app_object_id}')"
                }
            ]
        }



        chat_response = await http_client.post(
            "https://graph.microsoft.com/v1.0/chats",
            content=json.dumps(chat_body),
        )
        if chat_response.status_code not in {200, 201}:
            raise GraphSendError(
                f"Failed to create chat for '{user_principal_name}' ({chat_response.status_code}): {chat_response.text}"
            )
        chat_id = chat_response.json().get("id")
        if not chat_id:
            raise GraphSendError("Chat creation succeeded but response missing id")
        logger.debug(
            "Created Teams chat",
            extra={"user": user_principal_name, "chat_id": chat_id},
        )

        post_body = {
            "body": {
                "contentType": "html",
                "content": message,
            }
        }
        if subject:
            post_body["subject"] = subject

        message_response = await http_client.post(
            f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
            content=json.dumps(post_body),
        )
        if message_response.status_code not in {200, 201}:
            raise GraphSendError(
                f"Failed to send Teams message ({message_response.status_code}): {message_response.text}"
            )
        message_id = message_response.json().get("id")
        logger.info(
            "Teams message delivered",
            extra={
                "user": user_principal_name,
                "chat_id": chat_id,
                "message_id": message_id,
                "method": "teams",
            },
        )

    return f"Teams message delivered to {user_principal_name} (chat_id={chat_id}, message_id={message_id})"


def send_teams_message_sync(
    *,
    user_principal_name: str,
    message: str,
    subject: Optional[str] = None,
) -> str:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            send_teams_message(
                user_principal_name=user_principal_name,
                message=message,
                subject=subject,
            )
        )
    import nest_asyncio

    nest_asyncio.apply(loop)
    return loop.run_until_complete(
        send_teams_message(
            user_principal_name=user_principal_name,
            message=message,
            subject=subject,
        )
    )
