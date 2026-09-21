from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

from enums import (
    AccountType,
    CreditStatementStatus,
    OperationType,
    TransactionCategory,
    TransactionClassificationSource,
    TransactionStatus,
)


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, index=True, unique=True, primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    credit_score: Mapped[int] = mapped_column(default=500)
    password: Mapped[str] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(default=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="owner")
    cards: Mapped[list["Card"]] = relationship(back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(unique=True, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    type: Mapped[AccountType] = mapped_column(SQLEnum(AccountType))
    limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    iban: Mapped[str | None] = mapped_column(String(34), unique=True, index=True, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    grace_period_active: Mapped[bool] = mapped_column(default=True)
    acquired_interest: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cards: Mapped[list["Card"]] = relationship(back_populates="linked_account")
    owner: Mapped["User"] = relationship(back_populates="accounts")
    transactions_as_sender: Mapped[list["Transaction"]] = relationship(
        foreign_keys="[Transaction.sender_account_id]",
        back_populates="sender_account",
    )
    transactions_as_recipient: Mapped[list["Transaction"]] = relationship(
        foreign_keys="[Transaction.recipient_account_id]",
        back_populates="recipient_account",
    )
    credit_account_metrics: Mapped["CreditAccountMetrics | None"] = relationship(
        back_populates="linked_account",
        uselist=False,
        cascade="all, delete-orphan",
    )
    credit_statements: Mapped[list["CreditStatement"]] = relationship(
        back_populates="linked_account",
        cascade="all, delete-orphan",
    )


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    linked_acc_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    number: Mapped[str] = mapped_column(unique=True, index=True)
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    CVV_encrypted: Mapped[bytes] = mapped_column()
    pin_code_hashed: Mapped[str] = mapped_column()
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    linked_account: Mapped["Account"] = relationship(back_populates="cards")
    owner: Mapped["User"] = relationship(back_populates="cards")


class CreditAccountMetrics(Base):
    __tablename__ = "credit_account_metrics"

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        primary_key=True,
    )
    on_time_payments_count: Mapped[int] = mapped_column(default=0)
    total_missed_payments_count: Mapped[int] = mapped_column(default=0)
    current_days_past_due: Mapped[int] = mapped_column(default=0)
    max_days_past_due: Mapped[int] = mapped_column(default=0)
    rapid_limit_depletion_count: Mapped[int] = mapped_column(default=0)

    linked_account: Mapped["Account"] = relationship(
        back_populates="credit_account_metrics",
    )


class CreditStatement(Base):
    __tablename__ = "credit_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        index=True,
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    minimum_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    status: Mapped[CreditStatementStatus] = mapped_column(
        SQLEnum(CreditStatementStatus),
        default=CreditStatementStatus.OPEN,
        nullable=False,
    )
    minimum_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_in_full_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    interest_charged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    linked_account: Mapped["Account"] = relationship(
        back_populates="credit_statements",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(unique=True, primary_key=True)
    sender_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
    )
    recipient_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
    )
    sender_iban: Mapped[str | None] = mapped_column(index=True, nullable=True)
    recipient_iban: Mapped[str | None] = mapped_column(index=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus))
    operation_type: Mapped[OperationType] = mapped_column(SQLEnum(OperationType))
    description: Mapped[str | None] = mapped_column(nullable=True)
    category: Mapped[TransactionCategory] = mapped_column(
        SQLEnum(TransactionCategory),
        default=TransactionCategory.OTHER,
    )
    mcc_code: Mapped[str | None] = mapped_column(nullable=True)
    classification_source: Mapped[TransactionClassificationSource] = mapped_column(
        SQLEnum(TransactionClassificationSource),
        default=TransactionClassificationSource.SYSTEM,
        nullable=False,
    )

    sender_account: Mapped["Account | None"] = relationship(
        foreign_keys=[sender_account_id],
        back_populates="transactions_as_sender",
    )
    recipient_account: Mapped["Account | None"] = relationship(
        foreign_keys=[recipient_account_id],
        back_populates="transactions_as_recipient",
    )
