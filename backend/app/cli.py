"""ApplyKit administrative CLI for self-hosted installations."""

import typer

from app.auth.passwords import PasswordValidationError
from app.auth.service import OwnerNotConfigured, reset_owner_password
from app.database import SessionLocal

app = typer.Typer(help="ApplyKit administration commands.")
auth_app = typer.Typer(help="Protected-mode authentication commands.")
app.add_typer(auth_app, name="auth")


@auth_app.command("reset-password")
def reset_password_command() -> None:
    """Reset the installation owner password and revoke every active session."""
    password = typer.prompt(
        "New owner password",
        hide_input=True,
        confirmation_prompt=True,
    )
    try:
        with SessionLocal() as db:
            reset_owner_password(db, password)
    except PasswordValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except OwnerNotConfigured as exc:
        typer.echo(
            "Owner setup has not been completed. Start ApplyKit in password mode "
            "and use the one-time setup token first.",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    typer.echo("Owner password reset. All active sessions were signed out.")


if __name__ == "__main__":
    app()
