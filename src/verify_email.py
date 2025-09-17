# src/verify_email.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.auth_manager import verify_token
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI(title="SglTrack Email Verification")

# Allow cross-origin requests from your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sgltrack.com"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/verify_email", response_class=HTMLResponse)
def verify_email(token: str):
    """
    Verify the user's email based on token from email link
    """
    result = verify_token(token)
    if result["success"]:
        logger.info(f"Email verified successfully for token: {token}")
        html_content = """
        <html>
            <head><title>Email Verified</title></head>
            <body style="font-family:sans-serif; text-align:center; margin-top:50px;">
                <h1>✅ Email Verified Successfully!</h1>
                <p>You can now <a href="https://sgltrack.com">log in</a> to your account.</p>
            </body>
        </html>
        """
    else:
        logger.warning(f"Token verification failed: {result.get('error','Invalid or expired token')}")
        html_content = f"""
        <html>
            <head><title>Verification Failed</title></head>
            <body style="font-family:sans-serif; text-align:center; margin-top:50px;">
                <h1>❌ Verification Failed</h1>
                <p>{result.get('error','Invalid or expired token')}</p>
                <p>If the link expired, request a new verification email in your account portal.</p>
            </body>
        </html>
        """
    return HTMLResponse(content=html_content, status_code=200)

