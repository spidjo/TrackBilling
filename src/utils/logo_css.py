# utils/logo_css.py
"""
Shared CSS styles for SglTrack logo and branding
"""

def get_logo_css():
    """Return CSS for the SglTrack logo"""
    return """
    <style>
        /* SglTrack Logo Styles */
        .logo-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            transition: transform 0.3s ease;
        }

        .logo-wrapper:hover {
            transform: translateY(-2px);
        }

        .logo-icon {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, #800020, #008080);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(128, 0, 32, 0.2);
            flex-shrink: 0;
        }

        .logo-icon::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            animation: shine 3s infinite;
        }

        @keyframes shine {
            0% { left: -100%; }
            100% { left: 100%; }
        }

        .logo-icon-inner {
            width: 25px;
            height: 25px;
            border: 2px solid white;
            border-radius: 4px;
            position: relative;
        }

        .logo-icon-inner::after {
            content: '';
            position: absolute;
            bottom: 3px;
            left: 3px;
            right: 3px;
            height: 6px;
            background: white;
            border-radius: 2px;
        }

        .logo-content {
            display: flex;
            flex-direction: column;
        }

        .logo-text {
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 1.8rem;
            background: linear-gradient(135deg, #800020, #008080);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            margin: 0;
        }

        .logo-tagline {
            font-size: 0.7rem;
            color: #008080;
            margin-top: 2px;
            letter-spacing: 1px;
            font-weight: 500;
            margin: 0;
        }

        /* Responsive Logo */
        @media (max-width: 768px) {
            .logo-icon {
                width: 35px;
                height: 35px;
            }
            
            .logo-icon-inner {
                width: 20px;
                height: 20px;
            }
            
            .logo-text {
                font-size: 1.4rem;
            }
            
            .logo-tagline {
                font-size: 0.6rem;
            }
        }

        /* Logo in different contexts */
        .logo-hero .logo-icon {
            width: 60px;
            height: 60px;
        }

        .logo-hero .logo-icon-inner {
            width: 35px;
            height: 35px;
        }

        .logo-hero .logo-text {
            font-size: 2.5rem;
        }

        .logo-hero .logo-tagline {
            font-size: 0.9rem;
            letter-spacing: 2px;
        }

        .logo-small .logo-icon {
            width: 35px;
            height: 35px;
        }

        .logo-small .logo-text {
            font-size: 1.3rem;
        }

        .logo-small .logo-tagline {
            font-size: 0.6rem;
        }

        .logo-white .logo-text {
            color: white;
            background: none;
            -webkit-text-fill-color: white;
        }

        .logo-white .logo-tagline {
            color: rgba(255, 255, 255, 0.8);
        }

        /* Container Styles */
        .sidebar-logo {
            text-align: center;
            margin-bottom: 1.5rem;
            padding: 1rem 0;
            border-bottom: 1px solid #e5e7eb;
        }

        .sidebar-logo .logo-wrapper {
            justify-content: center;
        }

        .auth-logo-container {
            text-align: center;
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }

        .auth-logo-container .logo-wrapper {
            justify-content: center;
        }
    </style>
    """

def render_logo_html(size="normal", show_tagline=True, tagline_text="SAAS BILLING", white_text=False, container_class=""):
    """Render logo HTML with specified size and options - SIMPLIFIED VERSION"""
    size_class = f"logo-{size}" if size != "normal" else ""
    color_class = "logo-white" if white_text else ""
    
    # Single div structure to avoid nested div issues
    logo_html = f'''
    <div class="logo-wrapper {size_class} {color_class}">
        <div class="logo-icon">
            <div class="logo-icon-inner"></div>
        </div>
        <div class="logo-content">
            <div class="logo-text">SglTrack</div>
            {f'<div class="logo-tagline">{tagline_text}' if show_tagline else ''}
        
    </div>
    '''
    
    return logo_html

def render_logo_with_container(size="normal", show_tagline=True, tagline_text="SAAS BILLING", white_text=False, container_class=""):
    """Render logo with optional container wrapper"""
    logo_html = render_logo_html(size, show_tagline, tagline_text, white_text)
    
    if container_class:
        return f'<div class="{container_class}">{logo_html}</div>'
    
    return logo_html