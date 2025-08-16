from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import List
import os
from dotenv import load_dotenv
import secrets
from models import *
from pydantic_models import *
from database import  get_db
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from sqlalchemy.orm import Session

load_dotenv()
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_EMAIL = os.getenv("MAIL_EMAIL")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

conf = ConnectionConfig(
    MAIL_USERNAME = MAIL_EMAIL,
    MAIL_PASSWORD = MAIL_PASSWORD,
    MAIL_FROM = MAIL_EMAIL,
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="Himalayan Hut",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

class EmailSchema(BaseModel):
    email: List[EmailStr]

def generate_6_digit_code():
    return str(secrets.randbelow(900000) + 100000)

async def send_email_verification(email: str, user_id: int,type_ver: str, db: Session) -> Boolean:
    try:
        code = generate_6_digit_code()
        
        html = f"""<p>To login into HimalayanHut please enter this 6 digit code: {code}</p> """

        message = MessageSchema(
            subject="Himalayan Hut Sign-In Verification",
            recipients=[email],
            body=html,
            subtype=MessageType.html)

        fm = FastMail(conf)
        await fm.send_message(message)

        verify_db = Verification(
            user_id = user_id,
            email = email,
            code = code,
            type = type_ver
        )
        db.add(verify_db)
        db.commit()
        db.refresh(verify_db)

        
        return verify_db.id
    except Exception as e:
        return None