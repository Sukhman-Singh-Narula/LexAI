from sqlalchemy import Column, CHAR, String, DateTime, ForeignKey, Table, Boolean, Integer, ARRAY
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid

# Association tables for many-to-many relationships
advocate_cases = Table(
    'advocate_cases',
    Base.metadata,
    Column('advocate_id', CHAR(36), ForeignKey('advocates.id')),
    Column('case_id', CHAR(36), ForeignKey('cases.id'))
)

advocate_clients = Table(
    'advocate_clients',
    Base.metadata,
    Column('advocate_id', CHAR(36), ForeignKey('advocates.id')),
    Column('client_id', CHAR(36), ForeignKey('clients.id'))
)

class Advocate(Base):
    __tablename__ = 'advocates'
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    
    # Relationships
    cases = relationship("Case", secondary=advocate_cases, back_populates="advocate")
    clients = relationship("Client", secondary=advocate_clients, back_populates="advocates")
    documents = relationship("Document", back_populates="advocate")

class Case(Base):
    __tablename__ = 'cases'
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    case_type = Column(String(50), nullable=False)  # Added this field
    client_id = Column(CHAR(36), ForeignKey('clients.id'))
    description = Column(String(1000), nullable=True)
    filing_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    advocate = relationship("Advocate", secondary=advocate_cases, back_populates="cases")
    client = relationship("Client", back_populates="cases")
    documents = relationship("Document", back_populates="case")

class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    contact_number = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    
    # Relationships
    cases = relationship("Case", back_populates="client")
    advocates = relationship("Advocate", secondary=advocate_clients, back_populates="clients")

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    adv_id = Column(CHAR(36), ForeignKey('advocates.id'), nullable=False)
    case_id = Column(CHAR(36), ForeignKey('cases.id'), nullable=False)
    
    # Relationships
    advocate = relationship("Advocate", back_populates="documents")
    case = relationship("Case", back_populates="documents")