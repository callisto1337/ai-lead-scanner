from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    niches = relationship("Niche", back_populates="company")

    def __str__(self):
        return self.name


class Niche(Base):
    __tablename__ = "niches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    company = relationship("Company", back_populates="niches")
    config = relationship("NicheConfig", back_populates="niche")

    def __str__(self):
        return f"{self.name} [company_id={self.company_id}]"


class NicheConfig(Base):
    __tablename__ = "niche_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    niche_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("niches.id"),
        nullable=False,
        unique=True,
    )

    about: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extra_instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")

    niche = relationship("Niche", back_populates="config")

    def __str__(self):
        return f"Конфиг ниши #{self.niche_id}"


class NicheKeyword(Base):
    __tablename__ = "niche_keywords"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    niche_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("niches.id"),
        nullable=False,
    )

    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(TIMESTAMP(timezone=True))

    def __str__(self):
        return self.phrase


class NicheBlacklist(Base):
    __tablename__ = "niche_blacklist"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    niche_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("niches.id"),
        nullable=False,
    )

    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(TIMESTAMP(timezone=True))

    def __str__(self):
        return self.phrase


class LeadDestination(Base):
    __tablename__ = "lead_destinations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    niche_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("niches.id"),
        nullable=False,
    )

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_topic_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at = mapped_column(TIMESTAMP(timezone=True))

    def __str__(self):
        return f"{self.telegram_chat_id}:{self.telegram_topic_id or ''}"