# src/verify_email.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.auth_manager import verify_token, create_password_reset_token
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
        
        # Check if user has the default temporary password (invited admin)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = %s", (result["user_id"],))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and user_data[0] == 'password123':  # Has temporary password
            # For invited admin users, create a password reset token and redirect
            reset_token = create_password_reset_token(result["user_id"])
            if reset_token:
                reset_url = f"https://app.sgltrack.com/reset_password?token={reset_token}"
                logger.info(f"Redirecting invited admin user ID {result['user_id']} to password reset")
                return RedirectResponse(url=reset_url, status_code=302)
        
        # Regular users see success message
        html_content = """
        <html>
            <head><title>Email Verified</title></head>
            <body style="font-family:sans-serif; text-align:center; margin-top:50px;">
                <h1>✅ Email Verified Successfully!</h1>
                <p>You can now <a href="https://app.sgltrack.com">log in</a> to your account.</p>
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