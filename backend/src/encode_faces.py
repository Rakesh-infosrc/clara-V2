import os
import face_recognition
import pickle

# Directory with employee images (relative to backend/src)
IMAGE_DIR = "../employee_image"
ENCODINGS_FILE = "../data/dummy-data/encoding.pkl"

known_encodings = []
known_ids = []

print("[INFO] Processing images...")

for filename in os.listdir(IMAGE_DIR):
    if filename.lower().endswith((".jpg", ".png")):
        img_path = os.path.join(IMAGE_DIR, filename)
        image = face_recognition.load_image_file(img_path)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) > 0:
            encoding = encodings[0]
            known_encodings.append(encoding)

            # Extract employee ID from filename
            # Example: EMP001.jpg → EMP001
            employee_id = os.path.splitext(filename)[0]
            known_ids.append(employee_id)

            print(f"  ✔ Encoded Employee ID: {employee_id}")
        else:
            print(f"  ⚠ No face found in {filename}")

# Save encodings + employee IDs
data = {"encodings": known_encodings, "employee_ids": known_ids}
with open(ENCODINGS_FILE, "wb") as f:
    pickle.dump(data, f)

print(f"[INFO] Saved encodings to {ENCODINGS_FILE}")
