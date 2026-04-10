import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('./fit-tracker.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

print("Connected to Firestore")

# Test write
db.collection('test').add({"name": "test"})
print("Write successful")