import os
import json
import firebase_admin
from firebase_admin import credentials, auth

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    Supports Service Account JSON path, JSON string via env var, or Default Credentials.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        app = firebase_admin.initialize_app(cred)
        print(f"[Firebase Admin] Initialized using service account file: {service_account_path}")
        return app
    elif service_account_json:
        try:
            cert_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cert_dict)
            app = firebase_admin.initialize_app(cred)
            print("[Firebase Admin] Initialized using service account JSON string.")
            return app
        except Exception as e:
            print(f"[Firebase Admin Warning] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # Fallback to default app initialization (works with Firebase public ID token verification)
    try:
        app = firebase_admin.initialize_app()
        print("[Firebase Admin] Initialized using default configuration.")
        return app
    except Exception as err:
        print(f"[Firebase Admin Warning] Default initialization: {err}")
        return None

# Initialize on module load
try:
    initialize_firebase()
except Exception as e:
    print(f"[Firebase Admin Warning] Initialization error: {e}")

def verify_firebase_token(id_token: str) -> dict:
    """
    Verifies a Firebase ID token sent from the client.
    Returns decoded token payload if valid, containing 'uid', 'email', 'phone_number', etc.
    """
    if not id_token:
        raise ValueError("No token provided.")

    try:
        # Verify the ID token using Firebase Admin Auth
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Firebase token verification failed: {str(e)}")
