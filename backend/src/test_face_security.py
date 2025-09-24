#!/usr/bin/env python3
"""
Security test for face recognition system
"""

import os
from tools.face_recognition import run_face_verify

def test_with_dummy_image():
    """Test with a dummy/random image bytes to see security response"""
    # Create some dummy image bytes
    dummy_bytes = b'\xFF\xD8\xFF\xE0\x00\x10JFIF'  # JPEG header
    dummy_bytes += os.urandom(1000)  # Random data
    
    print("Testing face verification security with dummy data...")
    result = run_face_verify(dummy_bytes)
    print("Result:", result)

if __name__ == "__main__":
    test_with_dummy_image()