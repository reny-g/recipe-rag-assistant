import logging
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from main import RagSystem


logger = logging.getLogger(__name__)
system: Optional[RagSystem] = None
PUBLIC_DIR = Path(__file__).resolve().parent / "public"


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    session_id: str = Field(default="default", description="会话 ID")


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    cleared: bool


@asynccontextmanager
async def lifespan(_: FastAPI):
    global system
    logger.info("Initializing RagSystem for FastAPI service")
    system = RagSystem()
    system.build_knowledge_base()
    yield
    logger.info("FastAPI service shutdown")


app = FastAPI(
    title="Recipe RAG Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=PUBLIC_DIR / "assets"), name="assets")
app.mount("/vendor", StaticFiles(directory=PUBLIC_DIR / "vendor"), name="vendor")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if system is None:
        raise HTTPException(status_code=503, detail="RAG system is not ready")

    answer = system.answer_query(request.query, session_id=request.session_id, stream=False)
    if not isinstance(answer, str):
        answer = "".join(answer)
    return ChatResponse(answer=answer, session_id=request.session_id)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    if system is None:
        raise HTTPException(status_code=503, detail="RAG system is not ready")

    stream = system.answer_query(request.query, session_id=request.session_id, stream=True)
    if isinstance(stream, str):
        stream = iter([stream])

    def event_stream() -> Generator[str, None, None]:
        yield _sse_event("start", {"session_id": request.session_id})
        try:
            for chunk in stream:
                if not chunk:
                    continue
                yield _sse_event("token", {"content": chunk})
            yield _sse_event("end", {"session_id": request.session_id})
        except Exception as exc:
            logger.exception("Streaming chat failed")
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.delete("/sessions/{session_id}", response_model=SessionResponse)
def clear_session(session_id: str) -> SessionResponse:
    if system is None:
        raise HTTPException(status_code=503, detail="RAG system is not ready")

    system.clear_session(session_id)
    return SessionResponse(session_id=session_id, cleared=True)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
