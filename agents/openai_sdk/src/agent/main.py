

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from config import load_config_yaml
from observability import setup_otel
from runtime import OpenAISDKRuntime


cfg = load_config_yaml()

setup_otel(cfg)

app = FastAPI(title=cfg["title"])
runtime = OpenAISDKRuntime(cfg)

FastAPIInstrumentor.instrument_app(app)

cors_origins = cfg["cors_origins"]
origins = (
    [o.strip() for o in cors_origins.split(",")]
    if isinstance(cors_origins, str)
    else cors_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

@app.post("/send")
async def send_message(req: MessageRequest):

    response_text = await runtime.send(req.message)
    return {"output": response_text}

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8300)
