#this file creates database and opens it using an engine

from models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

#link address for the database
DATABASE_URL = "sqlite:///bankapp.db"

#we create an engine
#this is like a bridge that connects DB with the app
#we turn off checking the same threads, SQL might get error message otherwise
#we use sqlalchemy, which won't get the threads mixed up
engine = create_engine(url=DATABASE_URL, connect_args={"check_same_thread":False})

#creating sessions for each user to access DB separately
Sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#create all tables from the child class objects that have saved their structure in the metadata
Base.metadata.create_all(bind=engine)

def get_db():
    db = Sessionlocal()
    try:
        yield db
    finally:
        db.close()
