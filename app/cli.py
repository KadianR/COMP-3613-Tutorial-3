"""Run from the project root with python app/cli.py COMMAND."""
import sys
from pathlib import Path

# Allow direct script execution as well as module execution.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contextlib import contextmanager
from datetime import date
from typing import Optional
import typer
from tabulate import tabulate
from app.database import create_db_and_tables, get_cli_session
from app.models import Customer, Listing, Rental
from app.services.rental_service import RentalService
from sqlmodel import select

cli = typer.Typer(help='Tutorial 3: game rentals. Staff operate this local CLI.')


@contextmanager
def service():
    create_db_and_tables()
    with get_cli_session() as session:
        try:
            yield RentalService(session)
        except ValueError as exc:
            session.rollback()
            typer.echo(f'Error: {exc}', err=True)
            raise typer.Exit(1)


def parse_date(value):
    return date.fromisoformat(value) if value else None


@cli.command('initialize')
def initialize():
    """Create all database tables without deleting existing data."""
    create_db_and_tables()
    typer.echo('Database ready.')


@cli.command()
def join(username: str, email: str, deposit: str = '100.00'):
    """Register a customer and record their joining deposit."""
    password = typer.prompt('Password', hide_input=True, confirmation_prompt=True)
    with service() as svc:
        c = svc.join(username, email, password, deposit)
        typer.echo(f'Customer {c.id}: {c.username} (active)')


@cli.command()
def customers():
    """Show customer IDs for the rental commands."""
    with service() as svc:
        rows = svc.session.exec(select(Customer).order_by(Customer.id)).all()
        typer.echo(tabulate([(c.id, c.username, c.status) for c in rows],
                            headers=['ID', 'Username', 'Status']))


@cli.command()
def add_game(title: str, platform: str = '', genre: str = '', rating: str = '', boxart: str = ''):
    """Add a game title to the catalogue."""
    with service() as svc:
        game = svc.add_game(title, platform, genre, rating, boxart)
        typer.echo(f'Game {game.id}: {game.title}')


@cli.command()
def catalogue():
    """View titles and their customer-owned copies, prices and availability."""
    with service() as svc:
        rows = []
        for game in svc.catalogue():
            if not game.listings:
                rows.append([game.id, game.title, game.platform, '-', '-', '-', 'No copies'])
            for item in game.listings:
                rows.append([game.id, game.title, game.platform, item.id, item.owner.username,
                             f'{item.price:.2f}', item.availability.value])
        typer.echo(tabulate(rows, headers=['Game', 'Title', 'Platform', 'Listing', 'Owner', 'Price', 'Availability'], disable_numparse=True))


@cli.command()
def list_game(customer_id: int, game_id: int, condition: str, price: str):
    """Submit a copy for rental; staff inspection is required next."""
    with service() as svc:
        listing = svc.list_game(customer_id, game_id, condition, price)
        typer.echo(f'Listing {listing.id} created; pending staff inspection.')


@cli.command()
def inspect(listing_id: int, condition: str, approved: bool = True):
    """Staff: inspect a submitted copy. Use --no-approved to reject it."""
    with service() as svc:
        listing = svc.inspect_listing(listing_id, condition, approved)
        typer.echo(f'Listing {listing.id}: {listing.availability.value}')


@cli.command()
def rent(customer_id: int, listing_id: int, days: int = 7, on: Optional[str] = None):
    """Rent an inspected copy. Optional --on is an ISO date (YYYY-MM-DD)."""
    with service() as svc:
        rental = svc.rent_game(customer_id, listing_id, days, parse_date(on))
        typer.echo(f'Rental {rental.id}; due {rental.return_date}; price {rental.price:.2f}')


@cli.command()
def rentals(customer_id: Optional[int] = None):
    """Show rental history and amounts currently due."""
    with service() as svc:
        query = select(Rental).order_by(Rental.id)
        if customer_id is not None:
            query = query.where(Rental.renter_id == customer_id)
        rows = svc.session.exec(query).all()
        typer.echo(tabulate([(r.id, r.renter_id, r.listing_id, r.rental_date, r.return_date,
                              r.returned_at or '-', f'{svc.amount_due(r, r.returned_at):.2f}') for r in rows],
                            headers=['Rental', 'Customer', 'Listing', 'Start', 'Due', 'Returned', 'Charge'], disable_numparse=True))


@cli.command('return-game')
def return_game(customer_id: int, rental_id: int, amount: str, condition: str,
                on: Optional[str] = None, approved: bool = True):
    """Staff: inspect the returned copy and record payment in one transaction."""
    with service() as svc:
        payment = svc.return_game(customer_id, rental_id, amount, condition,
                                  parse_date(on), approved)
        typer.echo(f'Return complete. Payment {payment.id}: {payment.amount:.2f}')


if __name__ == '__main__':
    cli()
