"use client";

import { useEffect, useRef, useState } from "react";

interface VerificationState {
  status: 'scanning' | 'verified' | 'failed' | 'manual_input' | 'idle';
  message: string;
  employeeName?: string;
  employeeId?: string;
  accessGranted: boolean;
}

export default function VideoCapture() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const scanIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [verification, setVerification] = useState<VerificationState>({
    status: 'idle',
    message: 'Waiting for employee classification...',
    accessGranted: false
  });
  const [scanningEnabled, setScanningEnabled] = useState(false);
  const [mode, setMode] = useState<'idle' | 'employee' | 'visitor'>('idle');
  
  // Manual verification state
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualEmpId, setManualEmpId] = useState('');
  const [manualOtp, setManualOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  // Start camera feed
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => {
        console.error("Camera error:", err);
        setVerification({
          status: 'failed',
          message: 'Camera access denied',
          accessGranted: false
        });
      });
  }, []);

  // Check for signal from backend to start face recognition
  useEffect(() => {
    const checkSignal = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/get_signal');
        if (response.ok) {
          const signal = await response.json();
          if (signal && signal.name === 'start_face_capture') {
            setMode('employee');
            setScanningEnabled(true);
            setVerification({
              status: 'idle',
              message: 'Face recognition enabled - ready to scan',
              accessGranted: false
            });
          } else if (signal && signal.name === 'start_visitor_photo') {
            setMode('visitor');
            setScanningEnabled(true);
            setVerification({
              status: 'idle',
              message: 'Visitor photo capture enabled - ready to snap',
              accessGranted: false
            });
          }
        }
      } catch (error) {
        console.log('No signal endpoint available');
      }
    };

    const interval = setInterval(checkSignal, 2000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scan every 4 seconds when enabled and until verified
  useEffect(() => {
    if (!scanningEnabled || verification.status === 'verified' || verification.status === 'manual_input') {
      if (scanIntervalRef.current) {
        clearInterval(scanIntervalRef.current);
      }
      return;
    }

    scanIntervalRef.current = setInterval(() => {
      if (verification.status !== 'scanning') {
        scanFace();
      }
    }, 4000);

    return () => {
      if (scanIntervalRef.current) {
        clearInterval(scanIntervalRef.current);
      }
    };
  }, [verification.status, scanningEnabled]);

  // Face scanning function
  const scanFace = async () => {
    const video = videoRef.current;
    if (!video || !scanningEnabled || verification.status === 'verified') return;

    setVerification(prev => ({ ...prev, status: 'scanning', message: 'Scanning face...' }));

    try {
      // Draw video frame to canvas
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert to blob & send
      canvas.toBlob(async (blob) => {
        if (!blob) return;
        const formData = new FormData();
        formData.append("image", blob, "frame.jpg");

        try {
          const endpoint = mode === 'visitor' ? "http://127.0.0.1:8000/flow/visitor_photo" : "http://127.0.0.1:8000/face_verify";
          const res = await fetch(endpoint, {
            method: "POST",
            body: formData,
          });
          const data = await res.json();
          console.log("Scan result:", data);

          if (mode === 'visitor') {
            if (data.success) {
              setVerification({
                status: 'verified',
                message: data.message || '✅ Visitor photo captured',
                accessGranted: false
              });
              setScanningEnabled(false);
              alert(data.photo_result || data.message || 'Visitor photo saved');
            } else {
              setVerification({ status: 'failed', message: data.message || 'Visitor photo failed', accessGranted: false });
            }
            return;
          }

          if (data.success && data.verified) {
            setVerification({
              status: 'verified',
              message: data.message || `✅ Face recognized. Welcome ${data.employeeName}${data.employeeId ? ` (${data.employeeId})` : ''}!`,
              accessGranted: true,
              employeeName: data.employeeName,
              employeeId: data.employeeId
            });
            
            // Show success alert
            alert(`🎉 ${data.message || `Welcome ${data.employeeName}${data.employeeId ? ` (${data.employeeId})` : ''}!`}`);
          } else {
            setVerification({
              status: 'failed',
              message: 'Face not recognized',
              accessGranted: false
            });
          }
        } catch (err) {
          console.error("Verification error:", err);
          setVerification({
            status: 'failed',
            message: 'Network error',
            accessGranted: false
          });
        }
      }, "image/jpeg");
    } catch (error) {
      setVerification({
        status: 'failed',
        message: 'Scan failed',
        accessGranted: false
      });
    }
  };

  // Manual verification function
  const handleManualVerification = async () => {
    if (!manualName || !manualEmpId) {
      alert('Please provide both name and employee ID');
      return;
    }

    try {
      const response = await fetch('http://127.0.0.1:8000/employee_verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: manualName,
          employee_id: manualEmpId,
          otp: otpSent ? manualOtp : undefined
        })
      });

      const data = await response.json();
      
      if (data.success) {
        if (data.otp_sent) {
          setOtpSent(true);
          alert('OTP sent to your email!');
        } else if (data.verified) {
          setVerification({
            status: 'verified',
            message: `Welcome ${manualName}! Manual verification successful.`,
            accessGranted: true,
            employeeName: manualName
          });
          setShowManualInput(false);
        }
      } else {
        alert(data.message || 'Verification failed');
      }
    } catch (error) {
      alert('Network error during manual verification');
    }
  };

  const getStatusColor = () => {
    switch (verification.status) {
      case 'verified': return 'text-green-400';
      case 'scanning': return 'text-yellow-400';
      case 'failed': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = () => {
    switch (verification.status) {
      case 'verified': return '✅';
      case 'scanning': return '🔍';
      case 'failed': return '❌';
      default: return '👤';
    }
  };

  return (
    <div className="p-4 bg-gray-900 rounded-lg shadow-lg text-white min-w-[300px]">
      <div className="mb-3">
        <h3 className="text-lg font-semibold mb-2">Face Recognition</h3>
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          muted 
          className="rounded-lg w-full h-48 object-cover border-2 border-gray-700" 
        />
      </div>

      {/* Status Display */}
      <div className={`flex items-center mb-3 ${getStatusColor()}`}>
        <span className="mr-2 text-xl">{getStatusIcon()}</span>
        <span className="text-sm">{verification.message}</span>
      </div>

      {/* Access Status */}
      <div className="space-y-2">
        {verification.accessGranted && (
          <div className="p-3 bg-green-800 rounded-lg">
            <p className="text-green-200 text-sm">🔓 Full Access Granted</p>
            {verification.employeeName && (
              <p className="text-green-100 font-semibold">{verification.employeeName}{verification.employeeId ? ` (${verification.employeeId})` : ''}</p>
            )}
          </div>
        )}
      </div>

      {/* Manual Input Modal */}
      {showManualInput && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h3 className="text-lg font-semibold mb-4">Manual Verification</h3>
            
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Full Name"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
              />
              
              <input
                type="text"
                placeholder="Employee ID"
                value={manualEmpId}
                onChange={(e) => setManualEmpId(e.target.value)}
                className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
              />
              
              {otpSent && (
                <input
                  type="text"
                  placeholder="Enter OTP"
                  value={manualOtp}
                  onChange={(e) => setManualOtp(e.target.value)}
                  className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
                />
              )}
            </div>

            <div className="flex space-x-3 mt-6">
              <button
                onClick={handleManualVerification}
                className="flex-1 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
              >
                {otpSent ? 'Verify OTP' : 'Send OTP'}
              </button>
              
              <button
                onClick={() => {
                  setShowManualInput(false);
                  setOtpSent(false);
                  setManualName('');
                  setManualEmpId('');
                  setManualOtp('');
                }}
                className="flex-1 px-4 py-2 bg-gray-600 rounded hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
