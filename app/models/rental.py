"""Tutorial 3 model diagram, with snake_case field names."""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel
from app.models.user import UserBase


class Availability(str, Enum):
    PENDING = 'pending_inspection'
    AVAILABLE = 'available'
    RENTED = 'rented'
    UNAVAILABLE = 'unavailable'


class Customer(UserBase, table=True):
    # SQLModel table subclasses inherit a non-table base, rather than User's table.
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = 'pending_deposit'
    payments: list['Payment'] = Relationship(back_populates='customer')
    listings: list['Listing'] = Relationship(back_populates='owner')
    rentals: list['Rental'] = Relationship(back_populates='renter')

    def list_game(self, session, game, condition, price):
        from app.services.rental_service import RentalService
        return RentalService(session).list_game(self.id, game.id, condition, price)

    def rent_game(self, session, listing, days=7, today=None):
        from app.services.rental_service import RentalService
        return RentalService(session).rent_game(self.id, listing.id, days, today)

    def return_game(self, session, rental, amount, condition, today=None):
        from app.services.rental_service import RentalService
        return RentalService(session).return_game(self.id, rental.id, amount, condition, today)


class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    rating: str = ''
    platform: str = ''
    boxart: str = ''
    genre: str = ''
    listings: list['Listing'] = Relationship(back_populates='game')


class Listing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key='game.id')
    owner_id: int = Field(foreign_key='customer.id')
    condition: str
    availability: Availability = Availability.PENDING
    price: Decimal = Field(max_digits=10, decimal_places=2, gt=0)
    date_listed: date = Field(default_factory=date.today)
    game: Game = Relationship(back_populates='listings')
    owner: Customer = Relationship(back_populates='listings')
    rentals: list['Rental'] = Relationship(back_populates='listing')


class Rental(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key='listing.id')
    renter_id: int = Field(foreign_key='customer.id')
    rental_date: date = Field(default_factory=date.today)
    return_date: date  # agreed due date; returned_at records the actual return
    returned_at: Optional[date] = None
    price: Decimal = Field(max_digits=10, decimal_places=2, gt=0)
    late_fee_per_day: Decimal = Field(default=Decimal('5.00'), max_digits=10, decimal_places=2)
    listing: Listing = Relationship(back_populates='rentals')
    renter: Customer = Relationship(back_populates='rentals')
    payments: list['Payment'] = Relationship(back_populates='rental')

    def toJSON(self):
        return self.model_dump(mode='json')


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rental_id: Optional[int] = Field(default=None, foreign_key='rental.id')
    customer_id: int = Field(foreign_key='customer.id')
    payment_date: date = Field(default_factory=date.today)
    amount: Decimal = Field(max_digits=10, decimal_places=2, gt=0)
    purpose: str = 'rental'
    customer: Customer = Relationship(back_populates='payments')
    rental: Optional[Rental] = Relationship(back_populates='payments')

    def toJSON(self):
        return self.model_dump(mode='json')
