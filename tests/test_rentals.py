import os
os.environ.setdefault('DATABASE_URI', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('ENV', 'production')
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine, select
from app.models import Availability, Customer, Game, Listing, Payment, Rental
from app.services.rental_service import RentalService


@pytest.fixture
def service():
    engine = create_engine('sqlite://')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield RentalService(session)
    engine.dispose()


def setup_copy(svc):
    owner = svc.join('owner', 'owner@example.com', 'pass', '100')
    renter = svc.join('renter', 'renter@example.com', 'pass', '100')
    game = svc.add_game('Mario Kart', 'Switch')
    listing = svc.list_game(owner.id, game.id, 'Good', '25')
    return owner, renter, game, listing


def test_full_lifecycle_and_relationships(service):
    svc = service
    owner, renter, game, listing = setup_copy(svc)
    assert listing.game == game and listing.owner == owner
    assert listing in game.listings and listing in owner.listings
    with pytest.raises(ValueError, match='unavailable'):
        svc.rent_game(renter.id, listing.id)
    svc.inspect_listing(listing.id, 'Good', True)
    with pytest.raises(ValueError, match='own'):
        svc.rent_game(owner.id, listing.id)
    rental = svc.rent_game(renter.id, listing.id, 7, date(2026, 10, 1))
    assert rental in renter.rentals and rental in listing.rentals
    with pytest.raises(ValueError, match='unavailable'):
        svc.rent_game(renter.id, listing.id)
    assert svc.amount_due(rental, date(2026, 10, 10)) == Decimal('35')
    with pytest.raises(ValueError, match='different'):
        svc.return_game(owner.id, rental.id, '35', 'Good', date(2026, 10, 10))
    with pytest.raises(ValueError, match='equal'):
        svc.return_game(renter.id, rental.id, '25', 'Good', date(2026, 10, 10))
    assert rental.returned_at is None
    payment = svc.return_game(renter.id, rental.id, '35', 'Good', date(2026, 10, 10))
    assert payment in rental.payments and payment in renter.payments
    assert payment.toJSON()['amount'] == '35.00'
    assert rental.toJSON()['returned_at'] == '2026-10-10'
    assert listing.availability == Availability.AVAILABLE
    with pytest.raises(ValueError, match='already'):
        svc.return_game(renter.id, rental.id, '35', 'Good')
    assert len(svc.session.exec(select(Payment)).all()) == 3


def test_deposit_inspection_damage_and_price_snapshot(service):
    svc = service
    with pytest.raises(ValueError, match='deposit'):
        svc.join('x', 'x@example.com', 'pass', '10')
    owner, renter, game, listing = setup_copy(svc)
    svc.inspect_listing(listing.id, 'Scratched', False)
    with pytest.raises(ValueError):
        svc.rent_game(renter.id, listing.id)
    svc.inspect_listing(listing.id, 'Good', True)
    rental = svc.rent_game(renter.id, listing.id, 7, date(2026, 10, 1))
    listing.price = Decimal('99')
    svc.save(listing)
    assert svc.amount_due(rental, date(2026, 10, 8)) == Decimal('25')
    svc.return_game(renter.id, rental.id, '25', 'Damaged', date(2026, 10, 8), False)
    assert listing.availability == Availability.UNAVAILABLE


def test_invalid_amounts_and_inactive_member(service):
    svc = service
    owner, renter, game, listing = setup_copy(svc)
    for price in ['0', '-1', 'NaN', 'Infinity', '1.001']:
        with pytest.raises(ValueError):
            svc.list_game(owner.id, game.id, 'Good', price)
    renter.status = 'pending_deposit'
    svc.save(renter)
    with pytest.raises(ValueError, match='deposit'):
        svc.rent_game(renter.id, listing.id)
