import asyncio
import logging
import os
import time

import cv2
import jwt
import numpy as np
import psycopg2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")
JWT_ALGORITHM = "HS256"
REPEAT_WINDOW_SECONDS = 3.0

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "freshers_db"),
    user=os.getenv("DB_USER", "admin"),
    password=os.getenv("DB_PASSWORD"),
)

origins = [
    "https://incognito05.tech",
    "http://localhost:3000",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def decode_qr(frame_bytes: bytes) -> str | None:
    arr = np.frombuffer(frame_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    data, _points, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data or None


def verify_ticket(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "email"]},
        )
    except jwt.ExpiredSignatureError:
        return {"status": "error", "message": "Ticket has expired"}
    except jwt.InvalidTokenError:
        return {"status": "error", "message": "Invalid ticket"}

    email = payload["email"]

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tickets
                    SET is_used = TRUE
                    FROM users
                    WHERE tickets.user_id = users.user_id
                      AND users.email = %s
                      AND tickets.is_used = FALSE
                    RETURNING users.name
                    """,
                    (email,),
                )
                row = cur.fetchone()

                if row:
                    return {
                        "status": "success",
                        "message": "Verified successfully. Entry allowed.",
                        "name": row[0],
                    }

                cur.execute(
                    """
                    SELECT 1
                    FROM tickets
                    JOIN users ON tickets.user_id = users.user_id
                    WHERE users.email = %s
                    """,
                    (email,),
                )
                exists = cur.fetchone()

        if not exists:
            return {"status": "error", "message": "Invalid QR, no ticket found for this email"}
        return {"status": "error", "message": "QR already scanned, ticket already used"}

    except psycopg2.Error:
        logger.exception("Database error while verifying ticket")
        return {
            "status": "error",
            "message": "Server error, please scan again",
            "retryable": True,
        }
    finally:
        if conn is not None:
            conn.close()


@app.websocket("/ws/scan")
async def scan(ws: WebSocket):
    await ws.accept()
    last_token = None
    last_seen = 0.0
    last_result = None

    try:
        while True:
            frame = await ws.receive_bytes()

            token = await asyncio.to_thread(decode_qr, frame)

            if not token:
                await ws.send_json({"status": "searching"})
                continue

            now = time.monotonic()
            if token == last_token and now - last_seen < REPEAT_WINDOW_SECONDS:
                last_seen = now
                await ws.send_json(last_result)
                continue

            await ws.send_json({"status": "loading"})

            result = await asyncio.to_thread(verify_ticket, token)

            if not result.get("retryable"):
                last_token, last_seen, last_result = token, now, result
            await ws.send_json(result)

    except WebSocketDisconnect:
        pass