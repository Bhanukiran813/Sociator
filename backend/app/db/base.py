from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in Sociator.
    All database tables will inherit from this class.
    """
    pass
