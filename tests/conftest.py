import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Alert, Base, User

TEST_DB_FILE = "./test_ml_tracker.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture(autouse=True)
def _clean_test_db():
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    yield
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def test_engine(_clean_test_db):
    _engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def db_session_factory(test_engine):
    return sessionmaker(bind=test_engine)


@pytest.fixture
def sample_user(db_session):
    user = User(telegram_id=123456789, username="testuser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_alert(db_session, sample_user):
    alert = Alert(
        user_id=sample_user.id,
        item_id="MLC123456789",
        item_name="iPhone 15 128GB Negro",
        item_url="https://articulo.mercadolibre.cl/MLC-123456789-iphone-15",
        target_price=850_000,
        current_price=900_000,
        is_active=True,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert
