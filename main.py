from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from database import SessionLocal, engine, Base
from models import Advocate, Case, Client, Document
from utils.s3_utils import upload_to_s3, generate_presigned_url
import uuid
import os
from typing import List
import aiofiles
from pathlib import Path


# Initialize FastAPI app and database
app = FastAPI()
Base.metadata.create_all(bind=engine)
logging.basicConfig(level=logging.INFO)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register/advocate")
def register_advocate(
    name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    advocate = Advocate(name=name, email=email)
    db.add(advocate)
    try:
        db.commit()
        db.refresh(advocate)
        return {"advocate_id": advocate.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/client")
def register_client(
    name: str = Form(...),
    contact_number: str = Form(...),
    address: str = Form(...),
    db: Session = Depends(get_db)
):
    client = Client(name=name, contact_number=contact_number, address=address)
    db.add(client)
    try:
        db.commit()
        db.refresh(client)
        return {"client_id": client.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/case")
async def register_case(
    case_name: str = Form(...),
    advocate_id: str = Form(...),
    client_id: str = Form(...),
    case_type: str = Form(...),
    case_description: str = Form(None),
    filing_date: str = Form(None),
    db: Session = Depends(get_db)
):
    """Register a new case with the given details."""
    try:
        # Validate UUIDs
        uuid.UUID(advocate_id)
        uuid.UUID(client_id)
        
        # Check if advocate and client exist
        advocate = db.query(Advocate).filter(Advocate.id == advocate_id).first()
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not advocate:
            raise HTTPException(status_code=404, detail="Advocate not found")
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
            
        # Create new case
        new_case = Case(
            name=case_name,
            client_id=client_id,
            case_type=case_type,
            description=case_description,
            filing_date=filing_date
        )
        new_case.advocate.append(advocate)
        
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        
        return {
            "case_id": new_case.id,
            "message": "Case registered successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        db.rollback()
        logging.error(f"Case registration failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/case/{case_id}")
async def get_case(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve case details by case ID."""
    try:
        uuid.UUID(case_id)
        case = db.query(Case).filter(Case.id == case_id).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        return {
            "case_id": case.id,
            "name": case.name,
            "type": case.case_type,
            "description": case.description,
            "filing_date": case.filing_date,
            "client_id": case.client_id,
            "advocate_id": case.advocate[0].id if case.advocate else None
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID format")


ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file(file: UploadFile) -> None:
    """Validate file size and type."""
    # Check file size
    file_size = 0
    chunk_size = 1024
    while chunk := await file.read(chunk_size):
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024}MB"
            )
    
    # Reset file position after reading
    await file.seek(0)
    
    # Check file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to prevent path traversal and ensure safe characters."""
    # Get the file extension
    ext = Path(filename).suffix
    # Create a safe filename with UUID
    return f"{uuid.uuid4()}{ext}"

@app.post("/upload/document", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    advocate_id: str = Form(...),
    case_id: str = Form(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document for a specific case.
    
    Args:
        file: The file to upload
        advocate_id: ID of the advocate uploading the file
        case_id: ID of the case the document belongs to
        doc_type: Type of document being uploaded
        db: Database session
    
    Returns:
        dict: Contains document_id and url of the uploaded file
    
    Raises:
        HTTPException: For various error conditions
    """
    try:
        # Validate UUIDs
        try:
            uuid.UUID(advocate_id)
            uuid.UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        # Validate IDs and permissions
        advocate = db.query(Advocate).filter(Advocate.id == advocate_id).first()
        case = db.query(Case).filter(Case.id == case_id).first()
        
        if not advocate:
            raise HTTPException(status_code=404, detail="Advocate not found")
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        # Verify advocate has permission for this case
        if advocate not in case.advocate:
            raise HTTPException(
                status_code=403,
                detail="Advocate does not have permission for this case"
            )

        # Validate file
        await validate_file(file)
        
        # Sanitize filename and create unique file path
        safe_filename = sanitize_filename(file.filename)
        file_key = f"{advocate_id}/{case_id}/{doc_type}/{safe_filename}"
        
        try:
            # Upload to S3
            s3_url = await upload_to_s3(file, file_key)
        except Exception as e:
            logging.error(f"S3 upload failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )
        
        # Create document record
        document = Document(
            doc_type=doc_type,
            file_name=safe_filename,
            file_path=s3_url,
            adv_id=advocate_id,
            case_id=case_id
        )
        
        db.add(document)
        try:
            db.commit()
            db.refresh(document)
            return {
                "document_id": document.id,
                "url": s3_url,
                "file_name": safe_filename
            }
        except Exception as e:
            db.rollback()
            logging.error(f"Database operation failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Failed to save document record"
            )
            
    finally:
        # Ensure file is closed
        await file.close()