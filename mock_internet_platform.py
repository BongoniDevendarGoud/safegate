"""
SafeGate Prototype — Mock Public Internet Platforms
===================================================
Simulates public internet destination servers (e.g. video sharing platforms,
social networks, cloud storage providers) running at destination port 9000.

In the real world, this represents servers like YouTube, Instagram, TikTok,
or AWS S3 receiving uploads from worldwide users.

Without SafeGate:
- Any user can upload harmful deepfakes or explicit media directly.

With SafeGate as the Internet Mediator:
- All traffic must pass through SafeGate first.
- If SafeGate intercepts and drops malicious media, this destination server
  NEVER receives the file!
"""

import logging
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [INTERNET-DESTINATION] %(message)s")
logger = logging.getLogger("internet-destination")

app = FastAPI(
    title="Mock Public Internet Video Platform",
    description="Simulates a public internet destination (e.g. VideoShare / SocialCloud)",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "platform": "Mock Public Internet Video Hub",
        "status": "Online",
        "description": "Simulates public cloud video platforms accessible over the internet.",
    }


@app.post("/upload")
async def receive_public_upload(
    request: Request,
    file: UploadFile = File(...),
    channel: str = Form("public_feed"),
):
    """
    Simulated public internet upload receiver.
    Accepts video uploads published by clients across the internet.
    """
    content = await file.read()
    client_host = request.client.host if request.client else "unknown"

    logger.info(
        "RECEIVED VIDEO on Public Internet: '%s' (%d bytes) from client %s [Channel: %s]",
        file.filename,
        len(content),
        client_host,
        channel,
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "SUCCESS",
            "message": "Video successfully uploaded and published to the public internet!",
            "filename": file.filename,
            "bytes_received": len(content),
            "public_url": f"https://public-internet-media.mock/watch?v={file.filename}",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")
