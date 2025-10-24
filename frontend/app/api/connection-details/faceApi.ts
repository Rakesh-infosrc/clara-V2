// frontend\app\api\connection-details\faceApi.ts
export async function verifyFace(imageBlob: Blob) {
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  const formData = new FormData();
  formData.append("image", imageBlob, "capture.jpg");

  try {
    const response = await fetch(`${backendBase}/flow/face_recognition`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Face recognition flow failed:", error);
    return {
      success: false,
      verified: false,
      message: "Verification request failed",
    };
  }
}
