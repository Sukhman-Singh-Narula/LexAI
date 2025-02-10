import uuid
from datetime import datetime
from sqlalchemy import Column, CHAR, String, DateTime, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Define constants for table-level collation
TABLE_ARGS = {'mysql_charset': 'ascii', 'mysql_collate': 'ascii_general_ci'}
UUID_COLLATION = 'ascii_general_ci'

class FileMetadata(Base):
    __tablename__ = 'files'
    __table_args__ = TABLE_ARGS

    id = Column(CHAR(36, collation=UUID_COLLATION), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    case_id = Column(CHAR(36, collation=UUID_COLLATION), ForeignKey('cases.id'), nullable=False)
    lawyer_id = Column(CHAR(36, collation=UUID_COLLATION), ForeignKey('users.id'), nullable=False)
    s3_key = Column(String(512), unique=True, nullable=False)
    s3_url = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    version_id = Column(String(128), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    case = relationship("Case", back_populates="files")
    lawyer = relationship("User", back_populates="files")


class Case(Base):
    __tablename__ = 'cases'
    __table_args__ = TABLE_ARGS

    id = Column(CHAR(36, collation=UUID_COLLATION), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    client_id = Column(CHAR(36, collation=UUID_COLLATION), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    files = relationship("FileMetadata", back_populates="case", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = 'users'
    __table_args__ = TABLE_ARGS

    id = Column(CHAR(36, collation=UUID_COLLATION), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    files = relationship("FileMetadata", back_populates="lawyer", cascade="all, delete-orphan")
