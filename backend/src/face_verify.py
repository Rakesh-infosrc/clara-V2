# face_verify.py
import face_recognition
import pickle
import cv2
import numpy as np
import pandas as pd

ENCODINGS_FILE = r"known_faces.pkl"
EMPLOYEE_CSV = r"D:\learn\Virtual_Receptionist\backend\dummy-data\employee_details.csv"

# Load encodings
with open(ENCODINGS_FILE, "rb") as f:
    data = pickle.load(f)

# Load employee DB
employee_df = pd.read_csv(EMPLOYEE_CSV, dtype=str)
employee_df["EmployeeID"] = employee_df["EmployeeID"].str.strip().str.upper()

def run_face_verify(image_bytes: bytes):
    # Convert bytes → numpy array
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encs = face_recognition.face_encodings(rgb)

    if len(encs) == 0:
        return {"status": "error", "message": "No face detected"}

    input_enc = encs[0]

    matches = face_recognition.compare_faces(data["encodings"], input_enc, tolerance=0.5)
    face_distances = face_recognition.face_distance(data["encodings"], input_enc)

    if True in matches:
        best_idx = np.argmin(face_distances)
        emp_id = data["ids"][best_idx]

        # Lookup employee name from CSV
        emp_row = employee_df[employee_df["EmployeeID"] == emp_id]
        emp_name = emp_row.iloc[0]["Name"] if not emp_row.empty else "Unknown"

        return {
            "status": "success",
            "employeeId": emp_id,
            "name": emp_name,
            "message": f"Welcome {emp_name} ({emp_id})!"
        }

    return {"status": "error", "message": "Face not recognized"}
