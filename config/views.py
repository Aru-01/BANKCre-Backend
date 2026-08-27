from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
import django


def root_welcome_view(request):
    """
    Root landing view for BANCre Backend.
    Returns clean JSON for API clients and a premium status page for web browsers.
    """
    accept_header = request.META.get("HTTP_ACCEPT", "")

    # If requested by API client / Postman / fetch requesting JSON
    if "application/json" in accept_header and "text/html" not in accept_header:
        db_engine = settings.DATABASES["default"]["ENGINE"].split(".")[-1].capitalize()
        return JsonResponse(
            {
                "status": "online",
                "service": "BANCre Backend API",
                "version": "v1.0.0",
                "environment": "Development" if settings.DEBUG else "Production",
                "database": db_engine,
                "server_time": timezone.now().isoformat(),
                "documentation": {
                    "swagger_ui": request.build_absolute_uri("/docs/"),
                    "redoc": request.build_absolute_uri("/redoc/"),
                    "admin_panel": request.build_absolute_uri("/admin/"),
                },
                "api_modules": {
                    "auth": request.build_absolute_uri("/auth/"),
                    "properties": request.build_absolute_uri("/api/v1/properties/"),
                    "loans": request.build_absolute_uri("/api/v1/loans/"),
                    "memorandums": request.build_absolute_uri("/api/v1/memorandums/"),
                    "chatbot": request.build_absolute_uri("/api/v1/chatbot/"),
                    "notifications": request.build_absolute_uri("/api/v1/notifications/"),
                },
            },
            status=200,
            json_dumps_params={"indent": 2},
        )

    # Rich Premium HTML Landing for Web Browsers
    logo_url = getattr(
        settings, "COMPANY_LOGO_URL", "https://i.ibb.co.com/dw1P2S9K/BANCre.webp"
    )
    db_engine = settings.DATABASES["default"]["ENGINE"].split(".")[-1].capitalize()
    server_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    django_version = django.get_version()

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BANCre — API Server Status</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #07090e;
            --card-bg: rgba(18, 24, 38, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.35);
            --accent: #6366f1;
            --accent-cyan: #06b6d4;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.3);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 1.5rem;
            position: relative;
            overflow-x: hidden;
        }}
        /* Ambient Glow Background */
        .ambient-glow {{
            position: absolute;
            width: 550px;
            height: 550px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--primary-glow) 0%, rgba(99, 102, 241, 0.15) 50%, transparent 70%);
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            filter: blur(80px);
            z-index: 0;
            pointer-events: none;
        }}
        .container {{
            position: relative;
            z-index: 1;
            max-width: 820px;
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 3rem 2.5rem;
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px rgba(59, 130, 246, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}
        .brand-logo {{
            max-height: 52px;
            margin-bottom: 1.25rem;
            filter: drop-shadow(0 4px 12px rgba(59, 130, 246, 0.3));
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 1rem;
            box-shadow: 0 0 15px var(--success-glow);
        }}
        .pulse-dot {{
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.4); opacity: 0.6; }}
        }}
        h1 {{
            font-size: 2.25rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #ffffff 30%, #93c5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 1.05rem;
            font-weight: 300;
        }}
        /* Quick Action Buttons */
        .action-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2.5rem;
        }}
        .action-card {{
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.15rem 1.25rem;
            text-decoration: none;
            color: var(--text-main);
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .action-card:hover {{
            background: rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.4);
            transform: translateY(-3px);
            box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.25);
        }}
        .card-icon {{
            font-size: 1.5rem;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
        }}
        .card-info h3 {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.2rem;
        }}
        .card-info p {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        /* Endpoints Table */
        .section-title {{
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .endpoints-box {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.25rem;
            margin-bottom: 2rem;
        }}
        .endpoint-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.65rem 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.9rem;
        }}
        .endpoint-row:last-child {{
            border-bottom: none;
        }}
        .endpoint-name {{
            font-weight: 500;
            color: #d1d5db;
        }}
        .endpoint-path {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            background: rgba(59, 130, 246, 0.12);
            color: #93c5fd;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            border: 1px solid rgba(59, 130, 246, 0.25);
        }}
        /* System Info Footer */
        .system-meta {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            color: var(--text-muted);
            font-size: 0.82rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        .meta-item {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .meta-value {{
            color: #e5e7eb;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="ambient-glow"></div>
    <div class="container">
        <div class="header">
            <img src="{logo_url}" alt="BANCre Logo" class="brand-logo" onerror="this.style.display='none'">
            <div>
                <span class="status-badge">
                    <span class="pulse-dot"></span>
                    Operational &amp; Healthy
                </span>
            </div>
            <h1>BANCre Backend API</h1>
            <p class="subtitle">Commercial Real Estate Loan &amp; Memorandum Financing Platform</p>
        </div>

        <div class="action-grid">
            <a href="/docs/" class="action-card" target="_blank">
                <div class="card-icon">⚡</div>
                <div class="card-info">
                    <h3>Swagger UI</h3>
                    <p>Interactive API Testing</p>
                </div>
            </a>
            <a href="/redoc/" class="action-card" target="_blank">
                <div class="card-info" style="margin-left: 0.2rem;">
                    <h3>ReDoc Schema</h3>
                    <p>Comprehensive API Specs</p>
                </div>
            </a>
            <a href="/admin/" class="action-card" target="_blank">
                <div class="card-icon">🛡️</div>
                <div class="card-info">
                    <h3>Admin Console</h3>
                    <p>Unfold Database Admin</p>
                </div>
            </a>
        </div>

        <div class="section-title">📡 Active API Services</div>
        <div class="endpoints-box">
            <div class="endpoint-row">
                <span class="endpoint-name">🔐 Authentication &amp; User Profiles</span>
                <span class="endpoint-path">/auth/</span>
            </div>
            <div class="endpoint-row">
                <span class="endpoint-name">🏢 Real Estate Properties</span>
                <span class="endpoint-path">/api/v1/properties/</span>
            </div>
            <div class="endpoint-row">
                <span class="endpoint-name">💼 Loan Requests &amp; Quote Marketplace</span>
                <span class="endpoint-path">/api/v1/loans/</span>
            </div>
            <div class="endpoint-row">
                <span class="endpoint-name">📄 AI Offering Memorandums</span>
                <span class="endpoint-path">/api/v1/memorandums/</span>
            </div>
            <div class="endpoint-row">
                <span class="endpoint-name">🤖 AI Property Chatbot</span>
                <span class="endpoint-path">/api/v1/chatbot/</span>
            </div>
            <div class="endpoint-row">
                <span class="endpoint-name">🔔 Notifications &amp; Alerts</span>
                <span class="endpoint-path">/api/v1/notifications/</span>
            </div>
        </div>

        <div class="system-meta">
            <div class="meta-item">DB: <span class="meta-value">{db_engine}</span></div>
            <div class="meta-item">Django: <span class="meta-value">v{django_version}</span></div>
            <div class="meta-item">Clock: <span class="meta-value">{server_time}</span></div>
        </div>
    </div>
</body>
</html>
"""
    return HttpResponse(html_content, content_type="text/html")


def health_check_view(request):
    """
    Lightweight health check endpoint for monitoring, uptime trackers, and keep-alive pings.
    Takes ~1ms and consumes virtually 0% CPU/RAM.
    """
    from django.db import connection

    db_status = "connected"
    try:
        connection.ensure_connection()
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    is_healthy = db_status == "connected"
    return JsonResponse(
        {
            "status": "healthy" if is_healthy else "degraded",
            "service": "BANCre Backend",
            "database": db_status,
            "timestamp": timezone.now().isoformat(),
        },
        status=200 if is_healthy else 503,
    )

