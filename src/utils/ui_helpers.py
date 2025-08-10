import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
import time
import random
from functools import wraps

# Loading Animations
def display_loading_animation(text: str = "Processing...", animation_type: str = "dots"):
    """Display animated loading indicator that properly stops when context exits"""
    import threading
    
    class LoadingContext:
        def __init__(self, text, animation_type):
            self.text = text
            self.animation_type = animation_type
            self.placeholder = st.empty()
            self.stop_event = threading.Event()
            self.animation_thread = None

        def __enter__(self):
            self.animation_thread = threading.Thread(
                target=self._run_animation,
                daemon=True
            )
            self.animation_thread.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop_event.set()
            self.animation_thread.join()  # Wait for animation to stop
            self.placeholder.empty()

        def _run_animation(self):
            animations = {
                "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
                "bar": None,
                "spinner": ["|", "/", "-", "\\"]
            }
            
            if self.animation_type == "bar":
                progress = self.placeholder.progress(0)
                for i in range(100):
                    if self.stop_event.is_set():
                        break
                    progress.progress(i + 1)
                    time.sleep(0.02)
            else:
                chars = animations[self.animation_type]
                i = 0
                while not self.stop_event.is_set():
                    self.placeholder.markdown(f"{chars[i % len(chars)]} {self.text}")
                    time.sleep(0.1)
                    i += 1

    return LoadingContext(text, animation_type)

def loading_spinner(text: str = "Processing..."):
    """Simpler loading spinner"""
    return st.spinner(text)

# Form Helpers
def center_form(width: int = 500):
    """Center a form on the page with custom width"""
    st.markdown(
        f"""
        <style>
            .main > div {{
                max-width: {width}px;
                margin: 0 auto;
                padding: 1rem;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

def show_form_errors(errors: Dict[str, str], title: str = "Please fix the following errors:"):
    """Display form validation errors"""
    if errors:
        with st.container():
            st.error(title)
            for field, message in errors.items():
                st.markdown(f"• **{field.capitalize()}**: {message}")
            st.write("")  # Add spacing

# Notifications
def show_toast(message: str, type: str = "success", duration: int = 3):
    """Show temporary toast notification"""
    icons = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "ℹ️"
    }
    st.toast(message, icon=icons.get(type, "ℹ️"))
    if duration > 0:
        st.session_state['_toast_timeout'] = datetime.now() + timedelta(seconds=duration)

# Password Helpers
def validate_password(password: str) -> bool:
    """Check password meets complexity requirements"""
    return (
        len(password) >= 8 and
        any(c.islower() for c in password) and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()-_=+" for c in password)
    )

def password_strength_meter(password: str) -> None:
    """Visual password strength indicator"""
    strength = sum([
        len(password) >= 8,
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(c in "!@#$%^&*()-_=+" for c in password)
    ])
    
    colors = ["#ff4b4b", "#ffa700", "#ffa700", "#2ecc71", "#2ecc71"]
    labels = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    
    if password:
        st.markdown(
            f"""
            <div style="margin: -15px 0 15px;">
                <div style="height: 5px; background: #eee; border-radius: 5px;">
                    <div style="width: {strength * 20}%; height: 100%; 
                         background: {colors[strength-1]}; border-radius: 5px;"></div>
                </div>
                <div style="text-align: center; font-size: 0.8rem; color: {colors[strength-1]}">
                    {labels[strength-1]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Decorators
def with_loading_animation(func: Callable = None, *, text: str = "Processing..."):
    """Decorator to add loading animation to functions"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with display_loading_animation(text):
                return f(*args, **kwargs)
        return wrapper
    
    return decorator(func) if func else decorator