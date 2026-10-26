"""
FastAPI Web Server for eCourts Scraper UI.
Optimized for deployment on Render, Docker, and Cloud Environments.
"""

import os
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import requests
from ecourt import ECourtScraper
from ecourt.captcha import get_shared_solver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(
    title="eCourts Intelligence Portal",
    description="Automated CNR Case Search & Analytics with Neural Captcha Solving",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_event():
    """Pre-warms the neural network OCR model into memory on boot."""
    try:
        await asyncio.to_thread(get_shared_solver)
    except Exception as exc:
        print(f"[Warning] Solver pre-warm note: {exc}")


class SearchRequest(BaseModel):
    cnr: str
    retries: Optional[int] = 10


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html template not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/healthz")
async def healthz():
    """Health check endpoint for Render/Kubernetes."""
    return {"status": "ok"}


@app.post("/api/search")
async def search_case_post(req: SearchRequest):
    """Standard REST search endpoint returning full structured case details."""
    scraper = ECourtScraper()
    try:
        result = await asyncio.to_thread(scraper.search_case, req.cnr, req.retries or 10, None, False)
        return {"success": True, "data": result.model_dump()}
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"success": False, "error": str(exc)})
    except (ConnectionError, requests.exceptions.RequestException) as exc:
        err_msg = str(exc)
        if "timed out" in err_msg.lower() or "connecttimeout" in err_msg.lower():
            err_msg = (
                "Connection to eCourts India Gateway timed out. "
                "Indian government (*.gov.in) servers block traffic from foreign cloud datacenters (like Render US/EU). "
                "Set the ECOURT_PROXY environment variable in Render Dashboard with an Indian proxy to route requests."
            )
        return JSONResponse(status_code=504, content={"success": False, "error": err_msg})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})


@app.get("/api/search/stream")
async def search_case_stream(cnr: str = Query(..., min_length=16, max_length=16)):
    """
    Server-Sent Events (SSE) endpoint: streams real-time progress events
    and delivers the final structured case data.
    """
    queue: asyncio.Queue = asyncio.Queue()

    def progress_callback(step: str, message: str):
        queue.put_nowait({"type": "progress", "step": step, "message": message})

    async def worker():
        scraper = ECourtScraper()
        try:
            result = await asyncio.to_thread(
                scraper.search_case,
                cnr,
                10,
                None,
                False,
                progress_callback,
            )
            await queue.put({"type": "complete", "data": result.model_dump()})
        except LookupError as exc:
            await queue.put({"type": "not_found", "error": str(exc)})
        except (ConnectionError, requests.exceptions.RequestException) as exc:
            err_msg = str(exc)
            if "timed out" in err_msg.lower() or "connecttimeout" in err_msg.lower():
                err_msg = (
                    "Connection to eCourts India Gateway timed out. "
                    "Indian government (*.gov.in) servers block traffic from foreign cloud datacenters (like Render US/EU). "
                    "Set the ECOURT_PROXY environment variable in Render Dashboard with an Indian proxy to route requests."
                )
            await queue.put({"type": "error", "error": err_msg})
        except Exception as exc:
            await queue.put({"type": "error", "error": str(exc)})

    asyncio.create_task(worker())

    async def event_generator():
        while True:
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") in ("complete", "error", "not_found"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=False)
