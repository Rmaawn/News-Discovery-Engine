# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, Index

from .db import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    base_url = Column(String)
    language = Column(String)
    country = Column(String)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)

    source_id = Column(Integer, ForeignKey("sources.id"))
    url = Column(String, unique=True)

    status = Column(String, default="new")

    discovered_at = Column(DateTime, default=func.now())
    last_checked_at = Column(DateTime)

    retry_count = Column(Integer, default=0)

    error_message = Column(Text)

    source = relationship("Source")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)

    link_id = Column(Integer, ForeignKey("links.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))

    title = Column(String)
    author = Column(String)

    publish_date = Column(DateTime)

    raw_html = Column(Text)
    clean_text = Column(Text)

    image_url = Column(String)

    content_hash = Column(String, index=True)
    word_count = Column(Integer)

    created_at = Column(DateTime, default=func.now())

    link = relationship("Link")
    source = relationship("Source")


class AIProcessing(Base):
    __tablename__ = "ai_processing"

    id = Column(Integer, primary_key=True)

    article_id = Column(Integer, ForeignKey("articles.id"))

    rewritten_title = Column(Text)
    rewritten_content = Column(Text)

    created_at = Column(DateTime, default=func.now())

    article = relationship("Article")


class PublishLog(Base):
    __tablename__ = "publish_log"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    platform = Column(String)
    status = Column(String, default="pending")
    published_url = Column(String)
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("article_id", "platform", name="uq_publish_article_platform"),
        Index("ix_publish_platform_status_article", "platform", "status", "article_id"),
    )


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True)

    module = Column(String)

    level = Column(String)

    message = Column(Text)

    created_at = Column(DateTime, default=func.now())