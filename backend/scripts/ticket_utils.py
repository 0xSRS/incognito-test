import io
import json
import logging
import os
import re
import smtplib
import time
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler

import qrcode
from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "ticket_template.png")
QR_DIR = os.path.join(BASE_DIR, "qr")
PDF_DIR = os.path.join(BASE_DIR, "tickets")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in (QR_DIR, PDF_DIR, LOG_DIR):
    os.makedirs(d, exist_ok=True)

logger = logging.getLogger("freshers")
logger.setLevel(logging.INFO)

if not logger.handlers:  
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"), maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

email_logger = logging.getLogger("freshers.email")
email_logger.setLevel(logging.INFO)
email_logger.propagate = False  

if not email_logger.handlers:
    email_fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    email_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "email.log"), maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    email_file_handler.setFormatter(email_fmt)
    email_logger.addHandler(email_file_handler)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))      
SMTP_USER = os.getenv("SMTP_USER", "")              
SMTP_PASS = os.getenv("SMTP_PASS", "")              
FROM_NAME = os.getenv("FROM_NAME", "Incognito 5.0 Team")

QR_TARGET = 340        
CARD_PAD = 22          
CENTER_X = 450         
CENTER_Y = 830         


def safe_filename(name: str) -> str:
    """'Jay Vandara ' -> 'Jay Vandara'  (removes characters Windows/email don't allow)"""
    cleaned = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "ticket"


def _make_qr_image(payload: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        box_size=1,
        border=0,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  
    )
    qr.add_data(payload)
    qr.make(fit=True)
    modules = len(qr.get_matrix())

    
    px = max(3, QR_TARGET // modules)
    img = qr.make_image(fill_color="#B59410", back_color="black").convert("RGB")
    return img.resize((modules * px, modules * px), Image.NEAREST)


def create_ticket_pdf(name: str, email: str, token: str) -> tuple[str, str]:
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Poster not found: {TEMPLATE_PATH} (save it as ticket_template.png)")

    qr_img = _make_qr_image(token)

    base_name = safe_filename(name)
    qr_path = os.path.join(QR_DIR, f"{base_name}_{email.replace('@', '_at_')}.png")
    qr_img.save(qr_path)

  
    poster = Image.open(TEMPLATE_PATH).convert("RGB")
    card_size = qr_img.width + 2 * CARD_PAD
    card_x = CENTER_X - card_size // 2
    card_y = CENTER_Y - card_size // 2

    draw = ImageDraw.Draw(poster)
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_size, card_y + card_size],
        radius=14, fill="white", outline=(181, 148, 16), width=4,   
    )
    poster.paste(qr_img, (card_x + CARD_PAD, card_y + CARD_PAD))

    
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    buf.seek(0)

    pdf_path = os.path.join(PDF_DIR, f"{base_name}.pdf")
    if os.path.exists(pdf_path): 
        pdf_path = os.path.join(PDF_DIR, f"{base_name}_{int(time.time())}.pdf")

    page_w, page_h = poster.width * 0.5, poster.height * 0.5   
    c = canvas.Canvas(pdf_path, pagesize=(page_w, page_h))
    c.drawImage(ImageReader(buf), 0, 0, width=page_w, height=page_h)
    c.setTitle(f"Incognito 5.0 Ticket - {name}")
    c.save()

    logger.info(f"TICKET_CREATED | name={name} | email={email} | pdf={pdf_path}")
    return pdf_path, qr_path


def _build_html_email(name: str) -> str:
    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f2f2f2;font-family:Georgia,'Times New Roman',serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f2f2f2;padding:24px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background-color:#0d0d0d;border-radius:4px;overflow:hidden;">
            <tr>
              <td style="padding:40px 48px 36px 48px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td style="border:1px solid #b59410;border-radius:50%;width:64px;height:64px;text-align:center;vertical-align:middle;">
                      <span style="color:#d4af37;font-size:28px;">&#127917;</span>
                    </td>
                  </tr>
                </table>

                <p style="color:#c9a227;font-style:italic;font-size:16px;margin:28px 0 6px 0;">
                  An offer you cannot refuse
                </p>

                <h1 style="color:#d4af37;font-size:26px;margin:0 0 20px 0;font-weight:bold;">
                  Hi {name},
                </h1>

                <p style="color:#e8e2d0;font-size:15px;line-height:1.6;margin:0 0 18px 0;">
                  Congratulations on cracking the challenge. Your ticket for
                  <strong style="color:#d4af37;">Incognito 5.0 &mdash; The Waltz</strong> is attached to this email as a PDF.
                </p>

                <table cellpadding="0" cellspacing="0" style="margin:20px 0 24px 0;">
                  <tr>
                    <td style="color:#9a9a9a;font-size:13px;letter-spacing:1px;padding-right:14px;">DATE</td>
                    <td style="color:#e8e2d0;font-size:14px;">05 October 2026</td>
                  </tr>
                  <tr>
                    <td style="color:#9a9a9a;font-size:13px;letter-spacing:1px;padding-right:14px;">TIME</td>
                    <td style="color:#e8e2d0;font-size:14px;">3 PM &ndash; 7 PM</td>
                  </tr>
                  <tr>
                    <td style="color:#9a9a9a;font-size:13px;letter-spacing:1px;padding-right:14px;">VENUE</td>
                    <td style="color:#e8e2d0;font-size:14px;">Upper Auditorium</td>
                  </tr>
                </table>

                <p style="color:#e8e2d0;font-size:14px;line-height:1.6;margin:0 0 8px 0;">
                  Keep the QR code on your ticket ready at the entry gate. It is unique to you &mdash; please do not share it.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 48px;border-top:1px solid #2a2a2a;">
                <p style="color:#8a8a8a;font-size:12px;letter-spacing:1px;margin:0;">BEST REGARDS,</p>
                <p style="color:#c9a227;font-size:12px;letter-spacing:1px;margin:2px 0 0 0;">INCOGNITO ORGANISING COMMITTEE</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_ticket_email(email: str, name: str, pdf_path: str, retries: int = 3) -> bool:
   
    if not SMTP_USER or not SMTP_PASS:
        logger.error(f"EMAIL_FAILED | to={email} | reason=SMTP_USER/SMTP_PASS env vars not set | pdf={pdf_path}")
        email_logger.error(f"FAILED | to={email} | name={name} | reason=missing SMTP credentials")
        return False

    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = email
    msg["Subject"] = "Your Incognito 5.0 Freshers' Night Ticket"

    msg.set_content(
        f"Hi {name},\n\n"
        "Congratulations on cracking the challenge!\n"
        "Your ticket for Incognito 5.0 - The Waltz is attached to this email.\n\n"
        "Date  : 05 Oct 2026\nTime  : 3-7 PM\nVenue : Upper Auditorium\n\n"
        "Please keep the QR code ready at the entry gate. Do not share this ticket - it is unique to you.\n\n"
        "Best regards,\nIncognito Organising Committee"
    )
    msg.add_alternative(_build_html_email(name), subtype="html")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype="application", subtype="pdf",
            filename=f"{safe_filename(name)}.pdf",
        )

    for attempt in range(1, retries + 1):
        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            logger.info(f"EMAIL_SENT | to={email} | name={name} | attachment={safe_filename(name)}.pdf | attempt={attempt}")
            email_logger.info(f"SENT | to={email} | name={name} | attachment={safe_filename(name)}.pdf | attempt={attempt}")
            return True
        except Exception as e:
            logger.warning(f"EMAIL_RETRY | to={email} | attempt={attempt}/{retries} | error={e}")
            email_logger.warning(f"RETRY | to={email} | attempt={attempt}/{retries} | error={e}")
            time.sleep(2 * attempt)

    logger.error(f"EMAIL_FAILED | to={email} | name={name} | pdf={pdf_path} | all {retries} attempts failed")
    email_logger.error(f"FAILED | to={email} | name={name} | pdf={pdf_path} | all {retries} attempts failed")
    return False