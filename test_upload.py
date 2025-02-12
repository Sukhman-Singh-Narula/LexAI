import unittest
import requests
from dotenv import load_dotenv
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import uuid
import json

load_dotenv()

class TestDocumentUpload(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.base_url = "http://localhost:8000"
        self.session = self.create_session()
        
        # Use the provided IDs
        self.advocate_id = "02c20b1c-7325-40cc-92dc-35d33de9208f"
        self.client_id = "151deed3-ce59-4f2a-af97-3490b86b2891"
        self.case_id = "ac965b3d-5ab4-4c41-8268-709b6a17c281"
        
        print(f"Setup complete with provided IDs:\nAdvocate ID: {self.advocate_id}\nClient ID: {self.client_id}\nCase ID: {self.case_id}")

    def create_session(self):
        """Create a session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def create_test_file(self, filename="test.pdf"):
        """Create a temporary test file."""
        content = f"Test content created at {datetime.now()}"
        with open(filename, 'w') as f:
            f.write(content)
        return filename

    def test_successful_document_upload(self):
        """Test successful document upload."""
        test_file = self.create_test_file()
        
        try:
            with open(test_file, 'rb') as f:
                # Create MultipartEncoder for proper file upload
                files = {
                    'file': ('test_document.pdf', f, 'application/pdf')
                }
                data = {
                    'advocate_id': self.advocate_id,
                    'case_id': self.case_id,
                    'doc_type': 'LEGAL_DOCUMENT'  # Be explicit about document type
                }
                
                print(f"\nAttempting to upload document with data: {data}")
                response = self.session.post(
                    f"{self.base_url}/upload/document",
                    files=files,
                    data=data
                )
                
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.text}")
                
                if response.status_code != 200:
                    print(f"Error uploading document: {response.text}")
                    
                self.assertEqual(response.status_code, 200)
                
                response_data = response.json()
                self.assertIn("document_id", response_data)
                self.assertIn("url", response_data)
                self.assertIn("file_name", response_data)
                
                # Print successful upload details
                print(f"Document successfully uploaded:")
                print(f"Document ID: {response_data.get('document_id')}")
                print(f"URL: {response_data.get('url')}")
                print(f"File name: {response_data.get('file_name')}")
                
        except Exception as e:
            print(f"Exception during upload: {str(e)}")
            raise
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_upload_with_invalid_advocate(self):
        """Test document upload with invalid advocate ID."""
        test_file = self.create_test_file()
        
        try:
            with open(test_file, 'rb') as f:
                files = {
                    'file': ('test_document.pdf', f, 'application/pdf')
                }
                data = {
                    'advocate_id': str(uuid.uuid4()),
                    'case_id': self.case_id,
                    'doc_type': 'LEGAL_DOCUMENT'
                }
                
                response = self.session.post(
                    f"{self.base_url}/upload/document",
                    files=files,
                    data=data
                )
                
                self.assertEqual(response.status_code, 404)
                self.assertIn("detail", response.json())
                
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_upload_with_invalid_case(self):
        """Test document upload with invalid case ID."""
        test_file = self.create_test_file()
        
        try:
            with open(test_file, 'rb') as f:
                files = {
                    'file': ('test_document.pdf', f, 'application/pdf')
                }
                data = {
                    'advocate_id': self.advocate_id,
                    'case_id': str(uuid.uuid4()),
                    'doc_type': 'LEGAL_DOCUMENT'
                }
                
                response = self.session.post(
                    f"{self.base_url}/upload/document",
                    files=files,
                    data=data
                )
                
                self.assertEqual(response.status_code, 404)
                self.assertIn("detail", response.json())
                
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()

if __name__ == "__main__":
    print("🚀 Starting Document Upload API Tests...")
    unittest.main(verbosity=2)