from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_cv_template(profile_data: dict) -> str:
    template = env.get_template("cv/modern_v1.html")
    return template.render(profile=profile_data)


def render_cover_letter_template(letter_data: dict) -> str:
    template = env.get_template("cover_letter/standard_v1.html")
    return template.render(letter=letter_data)
