# src/utils/ui_helpers.py
import streamlit as st
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Callable, Any, Union, Tuple
import time
import random
from functools import wraps
import traceback

# ======================
# EMPTY STATE DISPLAY
# ======================

def display_empty_state(
    title: str,
    description: Optional[str] = None,
    icon: str = "ℹ️",
    width: Optional[int] = None,
    action: Optional[Tuple[str, Callable]] = None
) -> None:
    """
    Display a styled empty state message with optional action button.
    
    Args:
        title: Main title/message to display
        description: Additional descriptive text
        icon: Icon to display (emoji or icon name)
        width: Custom width for the container
        action: Tuple of (button_text, callback) for primary action
    """
    container = st.container(border=True)
    
    if width:
        container.markdown(
            f"<style>.st-emotion-cache-1h9usn1 {{width: {width}px !important;}}</style>",
            unsafe_allow_html=True
        )
    
    with container:
        # Center content
        st.markdown(
            """
            <style>
                .empty-state {
                    text-align: center;
                    padding: 2rem 1rem;
                }
                .empty-state-icon {
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown(
            f"""
            <div class="empty-state">
                <div class="empty-state-icon">{icon}</div>
                <h3>{title}</h3>
                {f'<p>{description}</p>' if description else ''}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if action:
            st.button(
                action[0],
                on_click=action[1],
                use_container_width=True,
                type="primary"
            )

# ======================
# ERROR HANDLING & DISPLAY
# ======================

def display_error(
    message: Union[str, Exception],
    details: Optional[str] = None,
    width: Optional[int] = None,
    dismissible: bool = True
) -> None:
    """
    Display a styled error message with optional details.
    
    Args:
        message: Main error message or Exception object
        details: Additional technical details to show
        width: Custom width for the error container
        dismissible: Whether to show a dismiss button
    """
    if isinstance(message, Exception):
        details = details or str(message)
        message = "An unexpected error occurred"
    
    container = st.container(border=True)
    
    if width:
        container.markdown(
            f"<style>.st-emotion-cache-1h9usn1 {{width: {width}px !important;}}</style>",
            unsafe_allow_html=True
        )
    
    with container:
        cols = st.columns([1, 20])  # For icon alignment
        with cols[0]:
            st.error("")  # Just for the icon
        with cols[1]:
            st.markdown(f"**{message}**")
        
        if details:
            with st.expander("Technical Details", expanded=False):
                st.code(details, language="text")
        
        if dismissible:
            st.button("Dismiss", key=f"dismiss_{random.randint(0, 1000)}")

def display_warning(message: str, details: Optional[str] = None) -> None:
    """Display a styled warning message"""
    container = st.container(border=True)
    with container:
        cols = st.columns([1, 20])
        with cols[0]:
            st.warning("")  # Just for the icon
        with cols[1]:
            st.markdown(f"**{message}**")
        
        if details:
            with st.expander("Details", expanded=False):
                st.text(details)

def handle_errors(func: Optional[Callable] = None, *, show_traceback: bool = False):
    """
    Decorator to handle and display errors gracefully.
    
    Args:
        show_traceback: Whether to display full traceback in error details
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                details = traceback.format_exc() if show_traceback else str(e)
                display_error(e, details=details)
                return None
        return wrapper
    
    return decorator(func) if func else decorator

# ======================
# LOADING ANIMATIONS
# ======================

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
            if self.animation_thread:
                self.animation_thread.join()
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

# ======================
# FORM HELPERS
# ======================

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
        with st.container(border=True):
            st.error(title)
            for field, message in errors.items():
                st.markdown(f"• **{field.capitalize()}**: {message}")
            st.write("")  # Add spacing

# ======================
# NOTIFICATIONS
# ======================

def show_toast(message: str, type: str = "success", duration: int = 3):
    """Show temporary toast notification"""
    icons = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "ℹ️"
    }
    st.toast(f"{icons.get(type, 'ℹ️')} {message}")
    if duration > 0:
        st.session_state['_toast_timeout'] = datetime.now() + timedelta(seconds=duration)

def show_success(message: str, duration: int = 3) -> None:
    """Display success message with auto-dismiss"""
    show_toast(message, "success", duration)

def show_failure(message: str, duration: int = 5) -> None:
    """Display error message with longer auto-dismiss"""
    show_toast(message, "error", duration)

# ======================
# PASSWORD HELPERS
# ======================

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

# ======================
# DECORATORS
# ======================

def with_loading_animation(func: Callable = None, *, text: str = "Processing..."):
    """Decorator to add loading animation to functions"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with display_loading_animation(text):
                return f(*args, **kwargs)
        return wrapper
    
    return decorator(func) if func else decorator

def with_error_handling(func: Optional[Callable] = None, *, show_traceback: bool = False):
    """
    Decorator to handle and display errors gracefully.
    
    Args:
        show_traceback: Whether to display full traceback in error details
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                details = traceback.format_exc() if show_traceback else str(e)
                display_error(e, details=details)
                return None
        return wrapper
    
    return decorator(func) if func else decorator

# Add this to src/utils/ui_helpers.py (anywhere in the file)

def format_date(date_obj: Union[datetime, date, str, None], format: str = "%d %b %Y") -> str:
    """
    Format a date object or ISO date string into a human-readable format.
    
    Args:
        date_obj: Date to format (datetime, date, or ISO string)
        format: Format string (default: "dd Mon YYYY")
    
    Returns:
        Formatted date string or "N/A" if invalid/None
    """
    if date_obj is None:
        return "N/A"
    
    if isinstance(date_obj, str):
        try:
            if "T" in date_obj:  # ISO format with time
                date_obj = datetime.fromisoformat(date_obj)
            else:  # Just date
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
        except ValueError:
            return "N/A"
    
    if isinstance(date_obj, (datetime, date)):
        return date_obj.strftime(format)
    
    return "N/A"