import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('creativecube-5987e-firebase-adminsdk-camur-0bd3dce788.json') # Replace with your actual path to the JSON file
firebase_admin.initialize_app(cred)

db = firestore.client()
