from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String
import uuid

class YTVideo(SQLModel, table=True):
    __tablename__ = "yt_video"
    
    video_id: str = Field(primary_key=True)
    url: str
    title: str
    author_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript: str
    duration: Optional[int] = Field(default=None)
    summary: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    threads: List["Thread"] = Relationship(back_populates="video")

class Thread(SQLModel, table=True):
    __tablename__ = "threads"
    
    thread_id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    video_id: str = Field(foreign_key="yt_video.video_id")
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    video: YTVideo = Relationship(back_populates="threads")
    messages: List["Message"] = Relationship(back_populates="thread")

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    
    message_id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = Field(foreign_key="threads.thread_id")
    sender: str
    content: str
    metadata_json: Optional[str] = Field(default=None, sa_column=Column("metadata", String)) # Using string for JSON for simplicity in SQLite or use specialized types if needed
    created_at: datetime = Field(default_factory=datetime.now)
    
    thread: Thread = Relationship(back_populates="messages")
