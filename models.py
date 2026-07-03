#this file has the schemas for the tables in our database
from datetime import datetime,timezone
from sqlalchemy import DateTime, String
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column

#create the Base variable. It will work as a parent class
Base = declarative_base()

#child class from base for the user table
class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(Integer, index=True, unique=True, primary_key=True)

    email : Mapped[str] = mapped_column(unique=True)
    first_name : Mapped[str] = mapped_column()
    last_name : Mapped[str] = mapped_column()
    credit_score : Mapped[int] = mapped_column(default=500)
    password : Mapped[str] = mapped_column()
    is_admin : Mapped[bool] = mapped_column(default=False)

    #User and Account are Python Class Objects
    #the DB users tabel won't have accounts as a separate column,
    #but the python object that will be used in our RAM will have accounts inside it
    accounts : Mapped[list["Account"]] = relationship(back_populates="owner")
    credit_cards : Mapped[list["CreditCard"]] = relationship(back_populates="owner")



class Account(Base):
    __tablename__ = "accounts"

    id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    owner_id : Mapped[int] = mapped_column(ForeignKey("users.id"))
    balance : Mapped[float] = mapped_column()
    type : Mapped[str] = mapped_column()
    overdraft_limit : Mapped[int] = mapped_column(default=0)
    iban : Mapped[str] = mapped_column(String(34), unique=True, index=True, nullable=False)

    debit_cards: Mapped[list["DebitCard"]] = relationship(back_populates="linked_account")
    owner : Mapped["User"] = relationship(back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"

    id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    sender_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.id"),nullable=True)
    recipient_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    sender_iban : Mapped[str | None] = mapped_column(index=True)
    recipient_iban : Mapped[str | None] = mapped_column(index=True)
    transfer_amount : Mapped[float] = mapped_column()
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default= lambda : datetime.now(timezone.utc),
                                                  nullable = False,
                                                  index = True
                                                     )
    status : Mapped[str] = mapped_column()
    operation_type : Mapped[str] = mapped_column()
    description : Mapped[str | None] = mapped_column(nullable=True)
    category : Mapped[str] = mapped_column()
    mcc_code : Mapped[str | None] = mapped_column(nullable=True)


class DebitCard(Base):
    __tablename__ = "debit_cards"

    id : Mapped[int] = mapped_column(primary_key=True)
    linked_acc_id : Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    number : Mapped[str] = mapped_column(unique=True, index=True)
    expiry_date : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    CVV_encrypted : Mapped[bytes] = mapped_column()
    pin_code_hashed : Mapped[str] = mapped_column()

    linked_account: Mapped["Account"] = relationship(back_populates="debit_cards")

class CreditCard(Base):
    __tablename__ = "credit_cards"

    id : Mapped[int] = mapped_column(primary_key=True)
    owner_id : Mapped[int] = mapped_column(ForeignKey("users.id"))
    number : Mapped[str] = mapped_column(unique=True, index=True)
    expiry_date : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    CVV_encrypted : Mapped[bytes] = mapped_column()
    pin_code_hashed : Mapped[str] = mapped_column()
    balance : Mapped[float] = mapped_column(default=0.0)
    credit_limit : Mapped[int] = mapped_column(default=500)

    owner: Mapped["User"] = relationship(back_populates="credit_cards")