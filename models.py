#this file has the schemas for the tables in our database
from datetime import datetime,timezone
from sqlalchemy import DateTime, String
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from typing import List

#create the Base variable. It will work as a parent class
Base = declarative_base()

#child class from base for the user table
class User(Base):
    __tablename__ = "users"

    user_id : Mapped[int] = mapped_column(Integer, index=True, unique=True, primary_key=True)

    email : Mapped[str] = mapped_column(unique=True)
    first_name : Mapped[str] = mapped_column()
    last_name : Mapped[str] = mapped_column()
    credit_score : Mapped[int] = mapped_column(default=500)
    password : Mapped[str] = mapped_column()
    is_admin : Mapped[bool] = mapped_column(default=False)

    #User and Account are Python Class Objects
    #the DB users tabel won't have accounts as a separate column,
    #but the python object that will be used in our RAM will have accounts inside it
    accounts : Mapped[List["Account"]] = relationship(back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    acc_id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    owner_id : Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    acc_balance : Mapped[float] = mapped_column()
    acc_type : Mapped[str] = mapped_column()
    overdraft_limit : Mapped[int] = mapped_column(default=0)
    iban : Mapped[str] = mapped_column(String(34), unique=True, index=True, nullable=False)

    owner : Mapped["User"] = relationship(back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    sender_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.acc_id"),nullable=True)
    recipient_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.acc_id"), nullable=True)
    transfer_amount : Mapped[float] = mapped_column()
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                     default= lambda : datetime.now(timezone.utc),
                                                     nullable = False
                                                     )
    status : Mapped[str] = mapped_column()
    operation_type : Mapped[str] = mapped_column()
    description : Mapped[str | None] = mapped_column(nullable=True)
    category : Mapped[str] = mapped_column()

    #    status : Literal["successful","failed"] = mapped_column()
    #