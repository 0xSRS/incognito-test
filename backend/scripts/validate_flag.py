import datetime
import time
from collections import defaultdict

import jwt
import psycopg2
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from ticket_utils import logger, create_ticket_pdf, send_ticket_email

app = FastAPI()

DB_CONFIG = dict(
    host="localhost",
    dbname="freshers_db",
    user="admin",
    password="q7w8e9a4s5d6z1x2c3@123",
)

JWT_SECRET = "mitulpagalhai"  

attempts = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts[ip] = [t for t in attempts[ip] if now - t < WINDOW_SECONDS]
    if len(attempts[ip]) >= MAX_ATTEMPTS:
        return True
    attempts[ip].append(now)
    return False


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


class FlagSubmission(BaseModel):
    flag: str


@app.post("/validate-flag")
async def validate_flag(payload: FlagSubmission, request: Request, background_tasks: BackgroundTasks):
    ip = request.client.host

    if is_rate_limited(ip):
        logger.warning(f"RATE_LIMITED | ip={ip}")
        raise HTTPException(429, "Too many attempts. Wait a bit and try again.")

    submitted_flag = payload.flag.strip()

    conn = get_conn()
    cur = conn.cursor()

    
    cur.execute(
        "SELECT flag_id, user_id, is_used FROM user_flags WHERE flag = %s",
        (submitted_flag,),
    )
    flag_row = cur.fetchone()
    if not flag_row:
        cur.close(); conn.close()
        logger.warning(f"INVALID_FLAG | ip={ip}")
        raise HTTPException(400, "Invalid flag")

    flag_id, user_id, is_used = flag_row
    if is_used:
        cur.close(); conn.close()
        logger.warning(f"FLAG_REUSED | ip={ip} | flag_id={flag_id} | user_id={user_id}")
        raise HTTPException(409, "This flag has already been redeemed")

    
    cur.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
    user_row = cur.fetchone()
    if not user_row:
        cur.close(); conn.close()
        logger.warning(f"INVALID_FLAG | ip={ip} | reason=user not found for user_id={user_id}")
        raise HTTPException(400, "Invalid flag")
    name, email = user_row

   
    cur.execute("UPDATE user_flags SET is_used = TRUE WHERE flag_id = %s", (flag_id,))
    conn.commit()

   
    token = jwt.encode(
        {
            "email": email,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=2),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    
    try:
        pdf_path, qr_path = create_ticket_pdf(name, email, token)
    except Exception:
        logger.exception(f"TICKET_FAILED | flag_id={flag_id} | user_id={user_id}")
        cur.execute("UPDATE user_flags SET is_used = FALSE WHERE flag_id = %s", (flag_id,))
        conn.commit()
        cur.close(); conn.close()
        raise HTTPException(500, "Could not generate ticket, please try again")

    
    cur.execute(
        "INSERT INTO tickets (user_id, flag_id, jwt_token, qr_path) VALUES (%s,%s,%s,%s)",
        (user_id, flag_id, token, pdf_path),
    )
    conn.commit()
    cur.close()
    conn.close()

   
    logger.info(f"FLAG_VALID | ip={ip} | user_id={user_id} | email={email}")
    background_tasks.add_task(send_ticket_email, email, name, pdf_path)

    return {"status": "success", "message": "Check your email for your ticket!"}