#this file has the schemas for the tables in our database
from datetime import datetime,timezone
from decimal import Decimal

from sqlalchemy import DateTime, String, JSON, Numeric
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy import Enum as SQLEnum

from enums import AccountType, TransactionStatus, OperationType, TransactionCategory

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
    cards : Mapped[list["Card"]] = relationship(back_populates="owner")





class Account(Base):
    __tablename__ = "accounts"

    id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    owner_id : Mapped[int] = mapped_column(ForeignKey("users.id"))
    balance : Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    type : Mapped[AccountType] = mapped_column(SQLEnum(AccountType))
    limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    iban : Mapped[str] = mapped_column(String(34), unique=True, index=True, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    #needed to calculate the credit percentages
    grace_period_active: Mapped[bool] = mapped_column(default=True)
    acquired_interest: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )

    cards: Mapped[list["Card"]] = relationship(back_populates="linked_account")
    owner : Mapped["User"] = relationship(back_populates="accounts")
    transactions_as_sender: Mapped[list["Transaction"]] = relationship(
                                                        foreign_keys="[Transaction.sender_account_id]",
                                                        back_populates="sender_account")
    transactions_as_recipient: Mapped[list["Transaction"]] = relationship(
                                                        foreign_keys="[Transaction.recipient_account_id]",
                                                        back_populates="recipient_account")


class Card(Base):
    __tablename__ = "cards"

    id : Mapped[int] = mapped_column(primary_key=True)
    linked_acc_id : Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    number : Mapped[str] = mapped_column(unique=True, index=True)
    expiry_date : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    CVV_encrypted : Mapped[bytes] = mapped_column()
    pin_code_hashed : Mapped[str] = mapped_column()
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    linked_account: Mapped["Account"] = relationship(back_populates="cards")
    owner: Mapped["User"] = relationship(back_populates="cards")





class Transaction(Base):
    __tablename__ = "transactions"

    id : Mapped[int] = mapped_column(unique=True, primary_key=True)
    sender_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.id"),nullable=True)
    recipient_account_id : Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    sender_iban : Mapped[str | None] = mapped_column(index=True, nullable=True)
    recipient_iban : Mapped[str | None] = mapped_column(index=True, nullable=True)
    amount : Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default= lambda : datetime.now(timezone.utc),
                                                  nullable = False,
                                                  index = True
                                                     )
    status : Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus))
    operation_type : Mapped[OperationType] = mapped_column(SQLEnum(OperationType))
    description : Mapped[str | None] = mapped_column(nullable=True)
    category : Mapped[TransactionCategory] = mapped_column(SQLEnum(TransactionCategory),
                                                           default=TransactionCategory.OTHER)
    mcc_code : Mapped[str | None] = mapped_column(nullable=True)

    sender_account : Mapped["Account | None" ] = relationship(foreign_keys=[sender_account_id],
                                                      back_populates="transactions_as_sender")
    recipient_account : Mapped["Account | None"] = relationship(foreign_keys=[recipient_account_id],
                                     back_populates="transactions_as_recipient")

