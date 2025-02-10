import os
import boto3
import logging
from dotenv import load_dotenv

load_dotenv()

# Initialize the S3 client using credentials from the environment
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def upload_to_s3(file, key):
    """
    Uploads a file object to S3 using the given key.
    Returns the URL of the uploaded file or None if the upload fails.
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    try:
        s3.upload_fileobj(file.file, bucket, key)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    except Exception as e:
        logging.error("Error uploading file: %s", e)
        return None

def get_s3_url(key):
    """
    Constructs and returns the S3 URL for a given object key.
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    return f"https://{bucket}.s3.amazonaws.com/{key}"

def delete_from_s3(key):
    """
    Deletes the file with the given key from the S3 bucket.
    Returns True if successful, False otherwise.
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        logging.error("Error deleting file: %s", e)
        return False

def generate_presigned_url(key, expiration=3600):
    """
    Generates a pre-signed URL for the given S3 object key.
    The URL will expire after 'expiration' seconds.
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    try:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logging.error("Error generating presigned URL: %s", e)
        return None
