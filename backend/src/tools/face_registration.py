"""
Face Registration Tool

This tool allows new employees to register their faces after manual verification
"""

import io
import os
import pickle
import pandas as pd
import face_recognition
import numpy as np
from datetime import datetime
from livekit.agents import function_tool, RunContext
from .config import ENCODING_FILE, EMPLOYEE_CSV


@function_tool()
async def register_employee_face(ctx: RunContext, employee_id: str, image_bytes: bytes) -> str:
    """
    Register a new employee's face after they've been manually verified.
    This updates the face encoding database.
    """
    try:
        print(f"Starting face registration for employee ID: {employee_id}")
        
        # Validate image data
        if not image_bytes or len(image_bytes) == 0:
            return "❌ No image data provided for face registration"
        
        # Load existing encodings
        try:
            with open(ENCODING_FILE, "rb") as f:
                encoding_data = pickle.load(f)
            known_encodings = encoding_data["encodings"]
            known_ids = encoding_data["employee_ids"]
        except FileNotFoundError:
            known_encodings = []
            known_ids = []
        
        # Check if employee ID exists in database
        try:
            df = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
            employee_match = df[df["EmployeeID"].str.strip().str.upper() == employee_id.strip().upper()]
            
            if employee_match.empty:
                return f"❌ Employee ID {employee_id} not found in employee database"
            
            employee_name = employee_match.iloc[0]["Name"]
        except Exception as e:
            return f"❌ Error reading employee database: {str(e)}"
        
        # Check if face is already registered
        if employee_id in known_ids:
            return f"❌ Face already registered for employee {employee_name} (ID: {employee_id})"
        
        # Process the new face image
        try:
            np_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            print(f"Image loaded successfully. Shape: {np_image.shape}")
        except Exception as e:
            return f"❌ Error loading image: {str(e)}"
        
        # Encode the face
        encodings = face_recognition.face_encodings(np_image)
        if not encodings:
            return "❌ No face detected in the image. Please ensure your face is clearly visible and try again."
        
        if len(encodings) > 1:
            print(f"Multiple faces detected ({len(encodings)}), using the first one")
        
        new_encoding = encodings[0]
        print(f"Face encoding generated successfully for {employee_name}")
        
        # Quality check - compare with existing faces to avoid duplicates
        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, new_encoding)
            min_distance = min(distances) if distances else 1.0
            
            # If the face is too similar to an existing one, warn but still register
            if min_distance < 0.4:
                closest_id = known_ids[distances.argmin()]
                print(f"Warning: Face is similar to existing employee {closest_id} (distance: {min_distance})")
        
        # Add the new encoding
        known_encodings.append(new_encoding)
        known_ids.append(employee_id)
        
        # Save updated encodings
        updated_encoding_data = {
            "encodings": known_encodings,
            "employee_ids": known_ids
        }
        
        # Backup the old file first
        backup_file = ENCODING_FILE + f".backup_{int(datetime.now().timestamp())}"
        try:
            if os.path.exists(ENCODING_FILE):
                import shutil
                shutil.copy2(ENCODING_FILE, backup_file)
                print(f"Backup created: {backup_file}")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
        
        # Save the new encodings
        try:
            with open(ENCODING_FILE, "wb") as f:
                pickle.dump(updated_encoding_data, f)
            print(f"Face encodings updated successfully")
        except Exception as e:
            return f"❌ Error saving face encodings: {str(e)}"
        
        # Log the registration
        log_entry = {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "registration_time": datetime.now().isoformat(),
            "status": "registered"
        }
        print(f"Face registration completed: {log_entry}")
        
        return (
            f"✅ Face registration successful! 🎉\\n"
            f"Welcome {employee_name} (ID: {employee_id})\\n"
            f"Your face has been registered for quick access in the future.\\n"
            f"Next time, you can simply show your face to the camera for instant verification."
        )
        
    except Exception as e:
        error_msg = f"Face registration error: {str(e)}"
        print(f"❌ {error_msg}")
        return f"❌ {error_msg}"


@function_tool()
async def check_face_registration_status(ctx: RunContext, employee_id: str) -> str:
    """
    Check if an employee's face is already registered in the system
    """
    try:
        # Load existing encodings
        try:
            with open(ENCODING_FILE, "rb") as f:
                encoding_data = pickle.load(f)
            known_ids = encoding_data["employee_ids"]
        except FileNotFoundError:
            return f"❌ Face recognition system not initialized"
        
        if employee_id in known_ids:
            return f"✅ Face is registered for employee ID {employee_id}"
        else:
            return f"❌ No face registered for employee ID {employee_id}"
            
    except Exception as e:
        return f"❌ Error checking face registration status: {str(e)}"


@function_tool()
async def remove_face_registration(ctx: RunContext, employee_id: str) -> str:
    """
    Remove an employee's face registration (admin function)
    """
    try:
        # Load existing encodings
        try:
            with open(ENCODING_FILE, "rb") as f:
                encoding_data = pickle.load(f)
            known_encodings = encoding_data["encodings"]
            known_ids = encoding_data["employee_ids"]
        except FileNotFoundError:
            return f"❌ Face recognition system not initialized"
        
        if employee_id not in known_ids:
            return f"❌ No face registration found for employee ID {employee_id}"
        
        # Find and remove the employee's face
        index = known_ids.index(employee_id)
        removed_encoding = known_encodings.pop(index)
        removed_id = known_ids.pop(index)
        
        # Save updated encodings
        updated_encoding_data = {
            "encodings": known_encodings,
            "employee_ids": known_ids
        }
        
        # Backup first
        backup_file = ENCODING_FILE + f".backup_{int(datetime.now().timestamp())}"
        try:
            if os.path.exists(ENCODING_FILE):
                import shutil
                shutil.copy2(ENCODING_FILE, backup_file)
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
        
        # Save the updated encodings
        with open(ENCODING_FILE, "wb") as f:
            pickle.dump(updated_encoding_data, f)
        
        return f"✅ Face registration removed for employee ID {employee_id}"
        
    except Exception as e:
        return f"❌ Error removing face registration: {str(e)}"