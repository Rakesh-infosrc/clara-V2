// frontend\components\FaceVerifyResult.tsx
import React from "react";

const FaceVerifyResult: React.FC<{ result: any }> = ({ result }) => {
  if (result.status === "success") {
    return (
      <div className="mt-3 p-2 bg-green-200 rounded text-red-500">
        ✅ Verified: <b>{result.name}</b> (ID: {result.employeeId})
      </div>
    );
  }

  return (
    <div className="mt-3 p-2 bg-red-200 rounded">
      ❌ Error: {result.message || "Face not recognized"}
    </div>
  );
};

export default FaceVerifyResult;
