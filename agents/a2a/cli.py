import argparse
import asyncio
import os
import signal
import uuid

from typing import Any

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_artifact_text, get_message_text
from a2a.types import Message, Part, Role, SendMessageRequest, TaskState
from a2a.utils.constants import TransportProtocol


async def _handle_stream(
    stream: Any, current_task_id: str | None
) -> str | None:
    async for event in stream:
        if event.HasField('message'):
            print('Message:', get_message_text(event.message, delimiter=' '))
            return None

        if not current_task_id:
            if event.HasField('task'):
                current_task_id = event.task.id
                state_name = TaskState.Name(event.task.status.state)
                print('--- Task Started ---')
                print(f'Task [state={state_name}]')
                if state_name in (
                    'TASK_STATE_COMPLETED',
                    'TASK_STATE_FAILED',
                    'TASK_STATE_CANCELED',
                    'TASK_STATE_REJECTED',
                ):
                    current_task_id = None
                    print('--- Task Finished ---')
            else:
                raise ValueError(f'Unexpected first event: {event}')

        if event.HasField('status_update'):
            state_name = TaskState.Name(event.status_update.status.state)
            message_text = (
                ': '
                + get_message_text(
                    event.status_update.status.message, delimiter=' '
                )
                if event.status_update.status.HasField('message')
                else ''
            )
            print(f'TaskStatusUpdate [state={state_name}]{message_text}')
            if state_name in (
                'TASK_STATE_COMPLETED',
                'TASK_STATE_FAILED',
                'TASK_STATE_CANCELED',
                'TASK_STATE_REJECTED',
            ):
                current_task_id = None
                print('--- Task Finished ---')
        elif event.HasField('artifact_update'):
            print(
                f'TaskArtifactUpdate [name={event.artifact_update.artifact.name}]:',
                get_artifact_text(
                    event.artifact_update.artifact, delimiter=' '
                ),
            )
    return current_task_id


async def main() -> None:
    """Run the A2A terminal client."""
    parser = argparse.ArgumentParser(description='A2A Terminal Client')
    parser.add_argument('--url', default='http://127.0.0.1:41241', help='Agent base URL (used to fetch agent card)')
    parser.add_argument('--token', default=None, help='Bearer token for gateway authorization')
    parser.add_argument(
        '--transport',
        default=TransportProtocol.JSONRPC,
        help='Preferred transport (JSONRPC, HTTP+JSON)',
    )
    parser.add_argument(
        '--no-stream',
        action='store_true',
        help='Use non-streaming message:send instead of message:stream',
    )
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification (for self-signed certs)',
    )
    parser.add_argument(
        '--ca-cert',
        default="/Users/kgupta/Desktop/acuvity/backend/dev/data/certificates/ca-chain-external.pem",
        help='Path to CA certificate PEM file for TLS verification',
    )
    args = parser.parse_args()

    headers = {'Authorization': f'Bearer {args.token}'} if args.token else {}
    if args.no_verify_ssl:
        verify: bool | str = False
    elif args.ca_cert:
        verify = args.ca_cert
    else:
        verify = True

    # One shared client used for card resolution, transport, and messaging.
    httpx_client = httpx.AsyncClient(
        headers=headers,
        verify=verify,
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
    )

    config = ClientConfig(
        streaming=not args.no_stream,
        httpx_client=httpx_client,
    )
    if args.transport:
        config.supported_protocol_bindings = [args.transport]

    print(f'Connecting to {args.url} (preferred transport: {args.transport or "Any"})')

    resolver = A2ACardResolver(httpx_client, args.url)
    card = await resolver.get_agent_card()

    client = await create_client(card, client_config=config)

    actual_transport = getattr(client, '_transport', client)
    print(f'  Picked Transport: {actual_transport.__class__.__name__}')

    print('\nConnected! Send a message or type /quit to exit.')

    current_task_id = None
    current_context_id = str(uuid.uuid4())

    while True:
        try:
            loop = asyncio.get_running_loop()
            user_input = await loop.run_in_executor(None, input, 'You: ')
        except KeyboardInterrupt:
            break

        if user_input.lower() in ('/quit', '/exit'):
            break
        if not user_input.strip():
            continue

        message = Message(
            role=Role.ROLE_USER,
            message_id=str(uuid.uuid4()),
            parts=[Part(text=user_input)],
            task_id=current_task_id,
            context_id=current_context_id,
        )

        request = SendMessageRequest(message=message)

        try:
            stream = client.send_message(request)
            current_task_id = await _handle_stream(stream, current_task_id)
        except httpx.RequestError as e:
            print(f'Error communicating with agent: {e}')

    await client.close()
    await httpx_client.aclose()


if __name__ == '__main__':
    asyncio.run(main())