import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import get_db
from models import Base
from main import app
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

#create the testing DB in the RAM. It will be deleted after the tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

#creating engine, no need to check the threads in the sqlaclchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       connect_args={"check_same_thread":False},
                       poolclass=StaticPool)

#create a new session maker for testing
TestingSessionLocal = sessionmaker(autocommit=False,
                                   autoflush=False,
                                   bind=engine)


# this is a universal function for all tests
# it creates the DB in RAM, accesses it, lets us run tests
# at the end it cleans everything up and deleted DB from RAM
@pytest.fixture(scope="function")
def client():
    #create all tables in the testing DB
    Base.metadata.create_all(bind=engine)

    #access the testing DB
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # replace in app the real DB with the testing one
    app.dependency_overrides[get_db] = override_get_db

    # testing client is created, now we just use it in some testing function
    with TestClient(app) as test_client:
        yield test_client

    # delete everything from RAM
    Base.metadata.drop_all(bind=engine)

#create and login one user with helper func
@pytest.fixture()
def auth_headers(client):
    return  create_user_and_login(client,"john@example.com","John")



#helper function can be called separately from auth headers
#this way we test transactions by creating 2 users
def create_user_and_login(client, email, first_name):

    create = client.post("/users/",
                             json={
                             "first_name": first_name,
                             "last_name": "Test",
                             "email": email,
                             "password": "securepassword123"
                         }
                         )

    assert create.status_code == 200

    # now try to log in with the data from created user
    login = client.post("/auth/",
                        data={"username": email,
                              "password": "securepassword123"})

    assert login.status_code == 200

    data = login.json()
    token = data["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_account(client, headers, acc_type, balance):

    #create acc for authenticated user
    response = client.post("/accounts/",
                           json={"type"  : acc_type,
                                 "balance" : balance},
                           headers=headers
                           )

    assert response.status_code == 200

    return response.json()