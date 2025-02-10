import os
import uuid
import logging
from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, Case, FileMetadata
from utils.s3_utils import upload_to_s3, generate_presigned_url, delete_from_s3
from dotenv import load_dotenv

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Register a new user (advocate) and return the generated adv_id.
    """
    user = User(
        name=name,
        email=email,
        role=role
    )
    db.add(user)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error("Error registering user: %s", e)
        raise HTTPException(status_code=400, detail="User registration failed.")
    db.refresh(user)
    logging.info("User registered with ID: %s", user.id)
    return {"adv_id": user.id}

###############################################
# Endpoint to register a new case for an advocate
###############################################
@app.post("/registercase")
def register_case(
    adv_id: str = Form(...),
    case_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Register a new case for a given advocate.
    For this example, we use adv_id as the client_id.
    Returns the generated case_id.
    """
    # Validate adv_id as a proper UUID
    try:
        uuid_adv = uuid.UUID(adv_id)
    except Exception as e:
        logging.error("Invalid adv_id provided: %s", e)
        raise HTTPException(status_code=400, detail="Invalid adv_id provided.")

    new_case = Case(
        name=case_name,
        client_id=adv_id  # or convert/validate as needed
    )
    db.add(new_case)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error("Error registering case: %s", e)
        raise HTTPException(status_code=400, detail="Case registration failed.")
    db.refresh(new_case)
    logging.info("Case registered with ID: %s", new_case.id)
    return {"case_id": new_case.id}

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    adv_id: str = Form(...),
    case_id: str = Form(...),
    file_type: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate that the file_type is one of the allowed types
    allowed_types = {"petition", "evidence", "application", "miscellaneous"}
    if file_type not in allowed_types:
        logging.error("Invalid file_type provided: %s", file_type)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_type. Allowed values: {allowed_types}"
        )

    # Calculate file size
    try:
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset the file pointer
    except Exception as e:
        logging.error("Error computing file size: %s", e)
        raise HTTPException(status_code=500, detail="Error processing file size")

    # Construct the S3 key as {adv_id}/{case_id}/{file_type}/filename
    file_key = f"{adv_id}/{case_id}/{file_type}/{file.filename}"

    # Upload file to S3
    s3_url = upload_to_s3(file, file_key)
    print("s3_url", s3_url)
    if not s3_url:
        logging.error("Failed to upload file to S3: %s", file.filename)
        raise HTTPException(status_code=500, detail="Upload failed")

    # Create a new file metadata record; convert adv_id and case_id to UUID
    try:
        file_record = FileMetadata(
            file_name=file.filename,
            case_id=uuid.UUID(case_id),
            lawyer_id=uuid.UUID(adv_id),
            s3_key=file_key,
            s3_url=s3_url,
            file_size=file_size,
            file_type=file_type
        )
    except Exception as e:
        logging.error("Error creating file metadata record: %s", e)
        raise HTTPException(
            status_code=400,
            detail="Invalid IDs provided. Ensure adv_id and case_id are valid UUIDs."
        )

    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    logging.info("File uploaded successfully: %s", file_record.id)
    return {
        "message": "File uploaded successfully",
        "file_id": str(file_record.id),
        "s3_url": s3_url
    }

@app.get("/files/{file_id}")
def get_file(file_id: str, db: Session = Depends(get_db)):
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file_id format")
    
    file_record = db.query(FileMetadata).filter(
        FileMetadata.id == file_uuid,
        FileMetadata.is_deleted == False
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate a pre-signed URL for secure access
    presigned_url = generate_presigned_url(file_record.s3_key)
    if not presigned_url:
        logging.error("Failed to generate presigned URL for file: %s", file_record.id)
        raise HTTPException(status_code=500, detail="Could not generate access URL")
    
    return {
        "file_name": file_record.file_name,
        "presigned_url": presigned_url,
        "file_size": file_record.file_size,
        "file_type": file_record.file_type,
        "uploaded_at": file_record.uploaded_at
    }

@app.delete("/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file_id format")
    
    file_record = db.query(FileMetadata).filter(
        FileMetadata.id == file_uuid,
        FileMetadata.is_deleted == False
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Attempt to delete the file from S3
    success = delete_from_s3(file_record.s3_key)
    if not success:
        logging.error("Failed to delete file from S3: %s", file_record.s3_key)
        raise HTTPException(status_code=500, detail="Failed to delete file from storage")
    
    # Soft delete: mark the record as deleted (so you retain history)
    file_record.is_deleted = True
    db.commit()
    logging.info("File deleted successfully: %s", file_record.id)
    return {"message": "File deleted successfully"}
