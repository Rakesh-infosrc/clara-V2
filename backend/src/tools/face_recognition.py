import io
import pickle
import pandas as pd
import face_recognition
import numpy as np
from datetime import datetime
from livekit.agents import function_tool, RunContext
from .config import ENCODING_FILE, EMPLOYEE_CSV, MANAGER_VISIT_CSV


# ✅ Load encodings once
with open(ENCODING_FILE, "rb") as f:
    encoding_data = pickle.load(f)

known_encodings = encoding_data["encodings"]
known_ids = encoding_data["employee_ids"]

# ✅ Load employee details
employee_df = pd.read_csv(EMPLOYEE_CSV)
employee_map = dict(zip(employee_df["EmployeeID"], employee_df["Name"]))


# ---------------------------------------------------
# Pure function (can be used in API + agent)
# ---------------------------------------------------
def run_face_verify(image_bytes: bytes):
    """SECURE face verification with strict matching and comprehensive logging"""
    import time
    from datetime import datetime
    
    verification_id = int(time.time() * 1000)  # Unique ID for this verification
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n=== SECURITY VERIFICATION {verification_id} ===")
    print(f"Time: {timestamp}")
    print(f"Image size: {len(image_bytes)} bytes")
    
    try:
        
        # Validate image data
        if not image_bytes or len(image_bytes) == 0:
            return {"status": "error", "message": "No image data provided"}
        
        # Load image from bytes
        np_image = face_recognition.load_image_file(
            io.BytesIO(image_bytes)
        )
        
        print(f"Image loaded successfully. Shape: {np_image.shape}")

        # Encode faces
        encodings = face_recognition.face_encodings(np_image)
        if not encodings:
            print("No face detected in the image")
            return {"status": "error", "message": "No face detected in image"}

        if len(encodings) > 1:
            print(f"Multiple faces detected ({len(encodings)}), using the first one")
            
        face_encoding = encodings[0]
        print(f"Face encoding generated successfully")

        # Compare with known encodings using STRICT tolerance
        print(f"Comparing against {len(known_encodings)} known faces...")
        
        # Use very strict tolerance (0.4) and require multiple verification methods
        strict_tolerance = 0.4
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=strict_tolerance)
        
        # Also get face distances for additional validation
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        print(f"Face distances: {face_distances}")
        
        # Find the best match (lowest distance)
        if len(face_distances) > 0:
            best_match_index = face_distances.argmin()
            best_distance = face_distances[best_match_index]
            print(f"Best match distance: {best_distance} (threshold: {strict_tolerance})")
            
            # Additional security: require distance to be significantly better than tolerance
            security_threshold = 0.35  # Even more strict
            
            if best_distance <= security_threshold and matches[best_match_index]:
                # Double-check: ensure this is significantly better than other matches
                other_distances = [d for i, d in enumerate(face_distances) if i != best_match_index]
                if other_distances:
                    second_best = min(other_distances)
                    confidence_gap = second_best - best_distance
                    print(f"Confidence gap: {confidence_gap} (required: >0.1)")
                    
                    # Require significant gap between best and second-best match
                    if confidence_gap > 0.1:
                        emp_id = known_ids[best_match_index]
                        emp_name = employee_map.get(emp_id, "Unknown")
                        print(f"✅ SECURE Face match found: {emp_name} ({emp_id}) with high confidence")
                        return {"status": "success", "employeeId": emp_id, "name": emp_name}
                else:
                    # Only one face in database, accept if distance is very low
                    if best_distance <= 0.25:  # Ultra strict for single face
                        emp_id = known_ids[best_match_index]
                        emp_name = employee_map.get(emp_id, "Unknown")
                        print(f"✅ SECURE Face match found: {emp_name} ({emp_id}) - single face verification")
                        return {"status": "success", "employeeId": emp_id, "name": emp_name}
        
        print("❌ SECURITY: Face verification FAILED - No secure match found")
        print(f"Best distance was: {best_distance if 'best_distance' in locals() else 'N/A'}")
        print("Reason: Face does not meet strict security requirements")
        return {"status": "error", "message": "Face not recognized - Security verification failed"}

    except Exception as e:
        error_msg = f"SECURITY ERROR in verification {verification_id}: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"=== END VERIFICATION {verification_id} ===\n")
        return {"status": "error", "message": "Verification system error"}
    
    finally:
        print(f"=== END VERIFICATION {verification_id} ===\n")


# ---------------------------------------------------
# Agent tool wrapper (for LiveKit LLM agent)
# ---------------------------------------------------
@function_tool
def face_verify(ctx: RunContext, image_bytes: bytes):
    return run_face_verify(image_bytes)


@function_tool()
async def face_login(ctx: RunContext, image_bytes: bytes) -> str:
    """
    Verify face → directly greet employee → grant full access to tools.
    Combines face recognition + manager visit greeting.
    """
    result = run_face_verify(image_bytes)

    if result.get("status") != "success":
        return f"❌ Face not recognized: {result.get('message')}"

    emp_id = result["employeeId"]
    emp_name = result["name"]

    # Check manager visit
    try:
        df_mgr = pd.read_csv(MANAGER_VISIT_CSV, dtype=str).fillna("")
        df_mgr["EmployeeID_norm"] = df_mgr["EmployeeID"].str.strip().str.upper()
        df_mgr["Visit Date"] = pd.to_datetime(
            df_mgr["Visit Date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        mgr_match = df_mgr[
            (df_mgr["EmployeeID_norm"] == emp_id)
            & (df_mgr["Visit Date"] == today)
        ]

        if not mgr_match.empty:
            office = mgr_match.iloc[0].get("Office", "our office")
            manager = mgr_match.iloc[0].get("Manager Name", emp_name)
            return (
                f"✅ Welcome {emp_name}! 🎉\n"
                f"We're honored to have you visiting our {office} office today.\n"
                f"Hope you had a smooth and comfortable journey.\n"
                f"It was wonderful having you at our {office} office!\n"
                f"Thanks for taking the time—it really meant a lot to the whole {office} team.\n"
                f"🔑 You now have full access to all tools."
            )
    except FileNotFoundError:
        pass

    # Default greeting if no manager visit today
    return f"✅ Welcome {emp_name}! You now have full access to all tools."