"""FastAPI entrypoint for the simple-langgraph demo agent."""
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.middleware.cors import CORSMiddleware

from runtime import IbacDemoRuntime
from utils.demo_prompts_ui import load_demo_cards_for_api
from utils.paths import get_upload_dir

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

UPLOAD_DIR = get_upload_dir()

app = FastAPI(title="Simple LangGraph Demo Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_runtime = IbacDemoRuntime()


class MessageRequest(BaseModel):
    """Request body for JSON /send."""

    message: str


def _append_pdf_hint(message: str, saved_abs: str) -> str:
    hint = (
        f"\n\n[Attached PDF on server: {saved_abs}]\n"
        "Use the parse_file tool with this exact file_path to extract text, "
        "then fulfill the user's request."
    )
    base = message.strip()
    if not base:
        return (
            "I attached a PDF. Please parse it and help me based on its contents."
            + hint
        )
    return (base + hint).strip()


@app.post("/send")
async def send_message(request: Request):
    """Accept JSON {message} or multipart form (message + optional PDF file)."""
    content_type = request.headers.get("content-type", "")

    saved_abs: str | None = None

    if content_type.startswith("application/json"):
        body = await request.json()
        req = MessageRequest.model_validate(body)
        text = req.message.strip()
        if not text:
            raise HTTPException(status_code=400, detail="message is required")
        return await _runtime.run_turn(text)

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_msg = form.get("message")
        text = (raw_msg if isinstance(raw_msg, str) else str(raw_msg or "")).strip()
        upload = form.get("file")
        if isinstance(upload, list):
            upload = upload[0] if upload else None

        # Starlette's multipart parser returns starlette.datastructures.UploadFile.
        # fastapi.UploadFile subclasses that type, so checking Starlette accepts both.
        if upload is not None and isinstance(upload, StarletteUploadFile):
            name = upload.filename or "upload.pdf"
            if not name.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400,
                    detail="Only PDF attachments are supported (.pdf).",
                )
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
            try:
                dest.write_bytes(await upload.read())
            except Exception:
                logging.exception("Failed to read or save uploaded PDF")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save the uploaded file.",
                ) from None
            saved_abs = str(dest.resolve())
            logging.info("Saved PDF upload to %s", saved_abs)

        if not text.strip() and not saved_abs:
            raise HTTPException(
                status_code=400,
                detail="Send a non-empty message and/or attach a PDF.",
            )

        full_message = _append_pdf_hint(text, saved_abs) if saved_abs else text
        return await _runtime.run_turn(full_message)

    raise HTTPException(
        status_code=415,
        detail="Use Content-Type: application/json or multipart/form-data.",
    )


@app.get("/health")
def health():
    """Return a simple health-check response."""
    return {"status": "ok"}


@app.get("/scenarios")
def list_demo_scenarios():
    """Home-screen cards from prompt-scenarios/demo-prompts.txt (CWD-independent)."""
    return load_demo_cards_for_api()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8300))
    uvicorn.run(app, host="0.0.0.0", port=port)
