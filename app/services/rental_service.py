"""Business operations share the caller's SQLModel session."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import update
from sqlmodel import select
from app.models import Availability, Customer, Game, Listing, Payment, Rental

DEPOSIT = Decimal('100.00')
LATE_FEE = Decimal('5.00')


def money(value):
    try:
        value = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Enter a valid monetary amount.') from None
    if not value.is_finite() or value <= 0 or value != value.quantize(Decimal('0.01')):
        raise ValueError('Amount must be positive with at most two decimal places.')
    return value


class RentalService:
    def __init__(self, session):
        self.session = session

    def get(self, model, id):
        obj = self.session.get(model, id)
        if obj is None:
            raise ValueError(f'{model.__name__} {id} does not exist.')
        return obj

    def save(self, *objects):
        try:
            self.session.add_all(objects)
            self.session.commit()
            for obj in objects:
                self.session.refresh(obj)
            return objects[0]
        except Exception:
            self.session.rollback()
            raise

    def active_customer(self, id):
        customer = self.get(Customer, id)
        if customer.status != 'active':
            raise ValueError('Customer must pay the joining deposit before listing or renting.')
        return customer

    def join(self, username, email, password, deposit):
        from app.utilities.security import encrypt_password
        amount = money(deposit)
        if amount < DEPOSIT:
            raise ValueError(f'Joining deposit must be at least {DEPOSIT}.')
        if not username.strip() or not password:
            raise ValueError('Username and password are required.')
        if self.session.exec(select(Customer).where(
            (Customer.username == username) | (Customer.email == email)
        )).first():
            raise ValueError('Customer username or email already exists.')
        customer = Customer.model_validate(dict(username=username.strip(), email=email,
                            password=encrypt_password(password), role='customer', status='active'))
        payment = Payment(customer=customer, amount=amount, purpose='deposit')
        self.save(customer, payment)
        return customer

    def add_game(self, title, platform='', genre='', rating='', boxart=''):
        if not title.strip():
            raise ValueError('Game title is required.')
        return self.save(Game(title=title.strip(), platform=platform, genre=genre,
                              rating=rating, boxart=boxart))

    def catalogue(self):
        return self.session.exec(select(Game).order_by(Game.title)).all()

    def list_game(self, customer_id, game_id, condition, price):
        customer = self.active_customer(customer_id)
        game = self.get(Game, game_id)
        if not condition.strip():
            raise ValueError('Describe the game condition.')
        return self.save(Listing(owner=customer, game=game, condition=condition,
                                 price=money(price)))

    def inspect_listing(self, listing_id, condition, approved):
        listing = self.get(Listing, listing_id)
        if listing.availability == Availability.RENTED:
            raise ValueError('Rented games must be inspected through the return operation.')
        if not condition.strip():
            raise ValueError('Inspection condition is required.')
        listing.condition = condition
        listing.availability = Availability.AVAILABLE if approved else Availability.UNAVAILABLE
        return self.save(listing)

    def rent_game(self, customer_id, listing_id, days=7, today=None):
        customer = self.active_customer(customer_id)
        listing = self.get(Listing, listing_id)
        if listing.owner_id == customer.id:
            raise ValueError('Customers cannot rent their own games.')
        if days < 1:
            raise ValueError('Rental duration must be at least one day.')
        today = today or date.today()
        # Conditional update prevents two customers taking the same available copy.
        result = self.session.exec(update(Listing).where(
            Listing.id == listing_id, Listing.availability == Availability.AVAILABLE
        ).values(availability=Availability.RENTED))
        if result.rowcount != 1:
            self.session.rollback()
            raise ValueError('Listing is unavailable or has not passed inspection.')
        rental = Rental(listing_id=listing_id, renter_id=customer.id, rental_date=today,
                        return_date=today + timedelta(days=days), price=listing.price,
                        late_fee_per_day=LATE_FEE)
        return self.save(rental)

    def amount_due(self, rental, today=None):
        today = today or date.today()
        late_days = max(0, (today - rental.return_date).days)
        return rental.price + late_days * rental.late_fee_per_day

    def return_game(self, customer_id, rental_id, amount, condition, today=None, approved=True):
        rental = self.get(Rental, rental_id)
        if rental.renter_id != customer_id:
            raise ValueError('Rental belongs to a different customer.')
        if rental.returned_at is not None:
            raise ValueError('This rental has already been returned.')
        today = today or date.today()
        if today < rental.rental_date:
            raise ValueError('Return date cannot precede the rental date.')
        if not condition.strip():
            raise ValueError('Staff must record the return inspection condition.')
        amount = money(amount)
        due = self.amount_due(rental, today)
        if amount != due:
            raise ValueError(f'Payment must equal {due:.2f}, including any late fee.')
        result = self.session.exec(update(Rental).where(
            Rental.id == rental_id, Rental.returned_at.is_(None)
        ).values(returned_at=today))
        if result.rowcount != 1:
            self.session.rollback()
            raise ValueError('This rental has already been returned.')
        listing = rental.listing
        listing.condition = condition
        listing.availability = Availability.AVAILABLE if approved else Availability.UNAVAILABLE
        payment = Payment(rental_id=rental_id, customer_id=customer_id,
                          payment_date=today, amount=amount, purpose='rental')
        self.save(payment, listing)
        return payment
