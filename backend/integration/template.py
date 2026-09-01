from pathlib import Path

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


env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
env.filters["format_date_range"] = format_date_range


def render_cv_template(profile_data: dict) -> str:
    template = env.get_template("cv/modern_v1.html")
    return template.render(profile=profile_data)


def render_cover_letter_template(letter_data: dict) -> str:
    template = env.get_template("cover_letter/standard_v1.html")
    return template.render(letter=letter_data)
