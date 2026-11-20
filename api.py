"""Local API. Build requests run serially and write only beneath output/api."""
from __future__ import annotations

from pathlib import Path
import sys
from threading import Lock
import uuid

ROOT = Path(__file__).resolve().parent
if (ROOT / ".deps").is_dir():
    sys.path.insert(0, str(ROOT / ".deps"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="PixelForge", version="0.1.0",
              description="Local pixel-city / central walking-person asset pipeline")
BUILD_ROOT = ROOT / "output" / "api"
ASEPRITE = Path(r"D:\Steam\steamapps\common\Aseprite\Aseprite.exe")
BUILD_LOCK = Lock()


class BuildRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    use_llm: bool = False
    use_aseprite: bool = True


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "offline_default": True, "aseprite_available": ASEPRITE.is_file()}


@app.post("/build")
def build(request: BuildRequest) -> dict:
    from pixelforge.pipeline import run_pipeline
    job_id = uuid.uuid4().hex
    with BUILD_LOCK:
        try:
            result = run_pipeline(request.prompt, BUILD_ROOT / job_id,
                                  ASEPRITE if request.use_aseprite else None, request.use_llm)
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "result": result}


@app.get("/artifacts/{job_id}/{artifact_path:path}")
def artifact(job_id: str, artifact_path: str) -> FileResponse:
    if not (len(job_id) == 32 and all(c in "0123456789abcdef" for c in job_id)):
        raise HTTPException(status_code=404, detail="Unknown job")
    job_root = (BUILD_ROOT / job_id).resolve()
    target = (job_root / artifact_path).resolve()
    if not target.is_relative_to(job_root) or not target.is_file():
        raise HTTPException(status_code=404, detail="Unknown artifact")
    return FileResponse(target)
