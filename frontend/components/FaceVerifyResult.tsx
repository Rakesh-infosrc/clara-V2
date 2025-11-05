import React from 'react';

interface FaceVerifyResultData {
  status: 'success' | 'error' | string;
  name?: string;
  employeeId?: string;
  message?: string;
}

interface FaceVerifyResultProps {
  result: FaceVerifyResultData;
}

const FaceVerifyResult: React.FC<FaceVerifyResultProps> = ({ result }) => {
  if (result.status === 'success') {
    return (
      <div className="mt-3 rounded bg-green-200 p-2 text-red-500">
        ✅ Verified: <b>{result.name}</b> {result.employeeId ? `(ID: ${result.employeeId})` : null}
      </div>
    );
  }

  return (
    <div className="mt-3 rounded bg-red-200 p-2">
      ❌ Error: {result.message ?? 'Face not recognized'}
    </div>
  );
};

export default FaceVerifyResult;
