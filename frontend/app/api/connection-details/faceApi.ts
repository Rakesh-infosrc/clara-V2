// frontend\app\api\connection-details\faceApi.ts
import { BACKEND_BASE_URL } from '@/lib/utils';

export async function verifyFace(imageBlob: Blob) {
  const backendBase = BACKEND_BASE_URL;
  const formData = new FormData();
  formData.append('image', imageBlob, 'capture.jpg');

  try {
    const response = await fetch(`${backendBase}/flow/face_recognition`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Face recognition flow failed:', error);
    return {
      success: false,
      verified: false,
      message: 'Verification request failed',
    };
  }
}
