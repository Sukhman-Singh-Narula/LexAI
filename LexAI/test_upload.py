import requests
import os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = "http://localhost:8000"
TEST_FILE_PATH = "example.txt"
DOWNLOADED_FILE_PATH = "downloaded_example.txt"
DEFAULT_DOCUMENT_TYPE = "miscellaneous"

def create_session():
    """Create a session with retries."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

def create_test_file():
    """Ensure a test file exists."""
    if not os.path.exists(TEST_FILE_PATH):
        with open(TEST_FILE_PATH, "w") as f:
            f.write("This is a test file for API upload.")
        print(f"\033[93m⚠ Created test file: {TEST_FILE_PATH}\033[0m")
    else:
        print(f"\033[94m✓ Test file exists: {TEST_FILE_PATH}\033[0m")

def register_advocate(name="Test Advocate", email="advocate@example.com", role="Lawyer"):
    """Register a new advocate using /register and return the adv_id."""
    session = create_session()
    data = {
        "name": name,
        "email": email,
        "role": role
    }
    response = session.post(f"{BASE_URL}/register", data=data, timeout=10)
    session.close()
    if response.status_code == 200:
        adv_id = response.json().get("adv_id")
        print(f"\033[92m✓ Advocate registered successfully with adv_id: {adv_id}\033[0m")
        return adv_id
    else:
        print(f"\033[91m✗ Advocate registration failed with status {response.status_code}\033[0m")
        print("Error details:", response.text)
        return None

def register_case(adv_id, case_name="Test Case"):
    """Register a new case for the given advocate using /registercase and return the case_id."""
    session = create_session()
    data = {
        "adv_id": adv_id,
        "case_name": case_name
    }
    response = session.post(f"{BASE_URL}/registercase", data=data, timeout=10)
    session.close()
    if response.status_code == 200:
        case_id = response.json().get("case_id")
        print(f"\033[92m✓ Case registered successfully with case_id: {case_id}\033[0m")
        return case_id
    else:
        print(f"\033[91m✗ Case registration failed with status {response.status_code}\033[0m")
        print("Error details:", response.text)
        return None

def upload_file_once(adv_id, case_id, document_type=DEFAULT_DOCUMENT_TYPE):
    """Uploads a file only once using the provided advocate and case IDs."""
    try:
        create_test_file()  # Ensure test file exists

        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": (os.path.basename(TEST_FILE_PATH), f, "text/plain")}
            data = {
                "adv_id": adv_id,
                "case_id": case_id,
                "file_type": document_type
            }

            session = create_session()
            response = session.post(f"{BASE_URL}/upload", files=files, data=data, timeout=10)
            session.close()

            if response.status_code == 200:
                print(f"\033[92m✓ Upload successful for document_type: {document_type}\033[0m")
                response_data = response.json()
                saved_filename = response_data.get("s3_url")  # S3 URL returned by the API
                file_id = response_data.get("id")
                print(f"S3 Saved Filename: {saved_filename}, File ID: {file_id}")
                return saved_filename, file_id
            else:
                print(f"\033[91m✗ Upload failed with status {response.status_code}\033[0m")
                print("Error details:", response.text)
                return None, None
    except Exception as e:
        print(f"\033[91m✗ Upload test failed: {str(e)}\033[0m")
        return None, None

def get_download_url(adv_id, case_id, saved_filename, file_type=DEFAULT_DOCUMENT_TYPE):
    """Requests a presigned download URL from the API using provided IDs."""
    try:
        if not saved_filename:
            print(f"\033[93m⚠ Skipping download test: No valid file name\033[0m")
            return None

        session = create_session()
        # Adjust query parameters to match the API's expected names
        response = session.get(
            f"{BASE_URL}/download?adv_id={adv_id}&case_id={case_id}&file_type={file_type}&filename={saved_filename}",
            timeout=10
        )
        session.close()

        if response.status_code == 200:
            presigned_url = response.json().get("url")
            print(f"\033[92m✓ Retrieved presigned download URL\033[0m")
            return presigned_url
        else:
            print(f"\033[91m✗ Failed to get presigned URL with status {response.status_code}\033[0m")
            print("Error details:", response.text)
            return None
    except Exception as e:
        print(f"\033[91m✗ Download URL test failed: {str(e)}\033[0m")
        return None

def download_file(presigned_url):
    """Uses the presigned URL to download the file and verify integrity."""
    try:
        if not presigned_url:
            print(f"\033[93m⚠ Skipping file download: No valid URL\033[0m")
            return False

        session = create_session()
        response = session.get(presigned_url, timeout=10)
        session.close()

        if response.status_code == 200:
            with open(DOWNLOADED_FILE_PATH, "wb") as f:
                f.write(response.content)
            print(f"\033[92m✓ File successfully downloaded: {DOWNLOADED_FILE_PATH}\033[0m")

            # Verify the downloaded file's content
            with open(TEST_FILE_PATH, "r") as original, open(DOWNLOADED_FILE_PATH, "r") as downloaded:
                if original.read() == downloaded.read():
                    print(f"\033[92m✓ File integrity check passed\033[0m")
                    return True
                else:
                    print(f"\033[91m✗ File integrity check failed\033[0m")
                    return False
        else:
            print(f"\033[91m✗ Download request failed with status {response.status_code}\033[0m")
            print("Error details:", response.text)
            return False
    except Exception as e:
        print(f"\033[91m✗ File download test failed: {str(e)}\033[0m")
        return False

if __name__ == "__main__":
    print("🚀 Starting API Tests...\n")

    # Register an advocate
    advocate_id = register_advocate()
    if not advocate_id:
        print("Advocate registration failed. Aborting tests.")
        exit(1)

    # Register a case for the advocate
    case_id = register_case(advocate_id)
    if not case_id:
        print("Case registration failed. Aborting tests.")
        exit(1)

    # Upload File Once using the registered IDs
    saved_filename, file_id = upload_file_once(advocate_id, case_id, 'petition')

    # Get Presigned Download URL using the registered IDs
    presigned_url = get_download_url(advocate_id, case_id, saved_filename, 'petition')

    # Download File and Verify Integrity
    download_success = download_file(presigned_url)

    # Final Summary
    print("\n📌 **Test Summary:**")
    print(f"Advocate ID: {advocate_id}")
    print(f"Case ID: {case_id}")
    print(f"Presigned URL: {'\033[92m✓ Success\033[0m' if presigned_url else '\033[91m✗ Failed\033[0m'}")
    print(f"Download: {'\033[92m✓ Success\033[0m' if download_success else '\033[91m✗ Failed\033[0m'}")

    print("\n✅ All tests completed.")

