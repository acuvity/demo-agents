from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def extract_agent_response(
    runner: Runner,
    session_service: InMemorySessionService,
    message: str,
    cfg: dict,
    session_id: str | None = None,
) -> str:
    if session_id is None:
        session = await session_service.create_session(
            app_name=cfg["app_name"],
            user_id="default_user",
        )
        session_id = session.id

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="default_user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[-1].text

    return response_text
