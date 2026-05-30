"""Command-line interface for vigil."""

from __future__ import annotations

import sys
import threading

import typer
from rich.console import Console
from sqlmodel import Session, select

from .config import get_settings
from .db import engine, init_db
from .models import User
from .security import hash_password

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

app = typer.Typer(
    help="vigil — uptime & change monitoring (built on apikit + taskq).",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def init() -> None:
    """Create the database tables."""
    init_db()
    console.print("[green]Database initialized.[/green]")


@app.command("create-user")
def create_user(username: str = typer.Argument(...),
                password: str = typer.Option(..., prompt=True, hide_input=True,
                                             confirmation_prompt=True)) -> None:
    """Create a user account."""
    init_db()
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == username)).first():
            console.print(f"[red]User '{username}' already exists.[/red]")
            raise typer.Exit(1)
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()
    console.print(f"[green]Created user '{username}'.[/green]")


@app.command()
def serve(host: str = typer.Option("127.0.0.1", "--host"),
          port: int = typer.Option(8000, "--port", "-p")) -> None:
    """Run the web server (API + dashboard)."""
    import uvicorn

    init_db()
    uvicorn.run("vigil.app:app", host=host, port=port)


@app.command()
def worker(burst: bool = typer.Option(False, "--burst", help="Drain queued checks, then exit.")) -> None:
    """Run a taskq worker that executes queued checks."""
    from taskq import Worker

    from .tasks import queue

    init_db()
    w = Worker(queue)
    console.print("[cyan]Worker started[/cyan]" if not burst else "[cyan]Draining queue…[/cyan]")
    n = w.run(burst=burst, on_event=lambda kind, job: console.print(
        f"#{job.id} check_monitor {kind}"))
    if burst:
        console.print(f"[green]Processed {n} check(s).[/green]")


@app.command()
def scheduler() -> None:
    """Run the scheduler loop (enqueues due checks)."""
    from .scheduler import run_scheduler

    init_db()
    console.print("[cyan]Scheduler started[/cyan] (Ctrl+C to stop)")
    try:
        run_scheduler(on_tick=lambda n: n and console.print(f"enqueued {n} due check(s)"))
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


@app.command()
def run(host: str = typer.Option("127.0.0.1", "--host"),
        port: int = typer.Option(8000, "--port", "-p")) -> None:
    """Run everything in one process: web server + scheduler + worker."""
    import uvicorn

    from taskq import Worker

    from .scheduler import run_scheduler
    from .tasks import queue

    init_db()
    stop = threading.Event()
    threading.Thread(target=run_scheduler, kwargs={"stop": stop}, daemon=True).start()
    threading.Thread(target=lambda: Worker(queue).run(), daemon=True).start()
    console.print(f"[bold cyan]vigil running[/bold cyan] — dashboard at http://{host}:{port}")
    try:
        uvicorn.run(app="vigil.app:app", host=host, port=port)
    finally:
        stop.set()


if __name__ == "__main__":
    app()
