from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CHAR, BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base


class FileTypeEnum(str, Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"


class RequestTypeEnum(str, Enum):
    text = "text"
    file = "file"


class StatusEnum(str, Enum):
    pending = "pending"
    success = "success"
    error = "error"


class DomainNameEnum(str, Enum):
    general = "general"
    business = "business"
    technical = "technical"
    medical = "medical"


class Language(Base):
    __tablename__ = "language"

    lang_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    lang_name: Mapped[str] = mapped_column(String(100), nullable=False)


class Domain(Base):
    __tablename__ = "domain"

    domain_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_name: Mapped[DomainNameEnum] = mapped_column(
        SQLEnum(DomainNameEnum, name="domain_name_t", native_enum=True),
        nullable=False,
        default=DomainNameEnum.general,
    )


class Session(Base):
    __tablename__ = "session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    translations: Mapped[list["Translation"]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    files: Mapped[list["File"]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    logs: Mapped[list["Logs"]] = relationship(back_populates="session", cascade="all, delete-orphan", passive_deletes=True)


class Translation(Base):
    __tablename__ = "translation"
    __table_args__ = (
        UniqueConstraint("text_hash", "source_lang", "target_lang", "domain_id", name="uniq_translation_cache"),
        Index("idx_translation_lang", "source_lang", "target_lang"),
        Index("idx_translation_domain", "domain_id"),
    )

    trans_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    source_lang: Mapped[int] = mapped_column(Integer, ForeignKey("language.lang_id"), nullable=False)
    target_lang: Mapped[int] = mapped_column(Integer, ForeignKey("language.lang_id"), nullable=False)
    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domain.domain_id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("session.session_id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session: Mapped["Session | None"] = relationship(back_populates="translations")


class File(Base):
    __tablename__ = "file"

    file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    translated_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_lang: Mapped[int | None] = mapped_column(Integer, ForeignKey("language.lang_id"), nullable=True)
    target_lang: Mapped[int | None] = mapped_column(Integer, ForeignKey("language.lang_id"), nullable=True)
    domain_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("domain.domain_id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("session.session_id", ondelete="CASCADE"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    file_type: Mapped[FileTypeEnum | None] = mapped_column(
        SQLEnum(FileTypeEnum, name="file_type_t", native_enum=True), nullable=True
    )
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum, name="status_t", native_enum=True), default=StatusEnum.pending
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session | None"] = relationship(back_populates="files")
    segments: Mapped[list["FileSegment"]] = relationship(back_populates="file", cascade="all, delete-orphan", passive_deletes=True)


class FileSegment(Base):
    __tablename__ = "file_segment"
    __table_args__ = (Index("idx_file_segment_file", "file_id"),)

    segment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    segment_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    file: Mapped["File | None"] = relationship(back_populates="segments")


class Logs(Base):
    __tablename__ = "logs"
    __table_args__ = (
        Index("idx_logs_time", "request_time"),
        Index("idx_logs_session", "session_id"),
    )

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("session.session_id", ondelete="CASCADE"), nullable=True)
    request_type: Mapped[RequestTypeEnum | None] = mapped_column(
        SQLEnum(RequestTypeEnum, name="request_type_t", native_enum=True), nullable=True
    )
    translation_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("translation.trans_id", ondelete="CASCADE"), nullable=True)
    file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=True)
    status: Mapped[StatusEnum | None] = mapped_column(
        SQLEnum(StatusEnum, name="status_t", native_enum=True), nullable=True
    )
    request_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    session: Mapped["Session | None"] = relationship(back_populates="logs")
