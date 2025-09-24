// frontend\app\api\connection-details\faceApi.ts
export async function verifyFace(imageBlob: Blob) {
  const formData = new FormData();
  formData.append("image", imageBlob, "capture.jpg");

  try {
    const response = await fetch("http://localhost:8000/face_verify", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    return await response.json(); // { status: "success", employeeId, name } OR { status: "error" }
  } catch (error) {
    console.error("Face verification failed:", error);
    return { status: "error", message: "Verification request failed" };
  }
}
