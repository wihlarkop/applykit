from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"


def format_date_range(start: str | None, end: str | None) -> str:
    """Render a start-end date range, omitting whichever side is missing
    instead of Jinja's default stringification of None as the text "None"."""
    if not start and not end:
        return ""
    if not start:
        return end
    return f"{start} – {end or 'Present'}"


def safe_project_url(value: str | None) -> str | None:
    """Make web project links clickable without exposing other URI schemes."""
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        if not parsed.scheme:
            value = "https:" + value if value.startswith("//") else "https://" + value
            parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        return value
    except ValueError:
        return None


env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
env.filters["format_date_range"] = format_date_range
env.filters["safe_project_url"] = safe_project_url


def render_cv_template(profile_data: dict, spacing_scale: float = 1.0) -> str:
    template = env.get_template("cv/modern_v1.html")
    return template.render(profile=profile_data, spacing_scale=spacing_scale)


def render_cover_letter_template(letter_data: dict) -> str:
    template = env.get_template("cover_letter/standard_v1.html")
    return template.render(letter=letter_data)
