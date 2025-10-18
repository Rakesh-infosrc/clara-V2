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
  const backendBase = (typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000') : '');
  
  // Manual verification state
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualEmpId, setManualEmpId] = useState('');
  const [manualOtp, setManualOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  // Visitor info
  const [visitorName, setVisitorName] = useState<string>('');
  const [showVisitorInfoForm, setShowVisitorInfoForm] = useState(false);
  const [vName, setVName] = useState('');
  const [vPhone, setVPhone] = useState('');
  const [vPurpose, setVPurpose] = useState('');
  const [vHost, setVHost] = useState('');

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
        console.log('[VideoCapture] Polling signal endpoint...');
        const response = await fetch(`${backendBase}/get_signal`);
        if (response.ok) {
          const signal = await response.json();
          console.log('[VideoCapture] Received signal:', signal);
          if (signal && signal.name === 'start_face_capture') {
            console.log('[VideoCapture] Activating employee face capture mode');
            setMode('employee');
            setScanningEnabled(true);
            setVerification({
              status: 'idle',
              message: 'Face recognition enabled - ready to scan',
              accessGranted: false
            });
            // Clear the signal after processing
            console.log('[VideoCapture] Clearing processed start_face_capture signal');
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
            setTimeout(() => {
              scanFace(true);
            }, 500);
          } else if (signal && signal.name === 'start_visitor_info') {
            console.log('[VideoCapture] Switching to visitor info collection mode');
            setMode('visitor');
            setScanningEnabled(false); // don't scan yet; wait for info submission
            setShowVisitorInfoForm(true);
            setVerification({
              status: 'idle',
              message: 'Please fill visitor details to proceed',
              accessGranted: false
            });
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal && signal.name === 'start_visitor_photo') {
            console.log('[VideoCapture] Activating visitor photo capture mode');
            setMode('visitor');
            setScanningEnabled(true);
            setVerification({
              status: 'idle',
              message: 'Visitor photo capture enabled - ready to snap',
              accessGranted: false
            });
            // Clear the signal after processing
            console.log('[VideoCapture] Clearing processed start_visitor_photo signal');
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
            setTimeout(() => {
              scanFace(true);
            }, 500);
          }
        }
      } catch (error) {
        console.log('[VideoCapture] Signal polling error:', error);
      }
    };

    const interval = setInterval(checkSignal, 2000);
    return () => clearInterval(interval);
  }, [backendBase]);

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
  const scanFace = async (force: boolean = false) => {
    console.log('[VideoCapture] scanFace invoked. Mode:', mode, 'Status:', verification.status, 'Scanning enabled:', scanningEnabled);
    const video = videoRef.current;
    if (!video || (!scanningEnabled && !force) || verification.status === 'verified') return;

    const stream = (video.srcObject as MediaStream | null);
    const track = stream?.getVideoTracks?.()[0];
    const isLive = !!track && track.readyState === 'live' && video.videoWidth > 0;
    if (!isLive) {
      console.warn('[VideoCapture] Camera feed not live. Track status:', track?.readyState, 'videoWidth:', video.videoWidth);
      setVerification({
        status: 'failed',
        message: 'Camera feed not available. Please turn your camera on.',
        accessGranted: false,
      });
      setScanningEnabled(false);
      if (track && track.readyState !== 'live') {
        track.stop();
      }
      return;
    }

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
        if (mode === 'visitor' && visitorName.trim()) {
          formData.append('visitor_name', visitorName.trim());
        }

        try {
          const endpoint = mode === 'visitor' ? `${backendBase}/flow/visitor_photo` : `${backendBase}/face_verify`;
          console.log('[VideoCapture] Submitting frame to endpoint:', endpoint);
          const res = await fetch(endpoint, {
            method: "POST",
            body: formData,
          });
          let data: any = {};
          try {
            data = await res.json();
          } catch (e) {
            // ignore JSON parse errors
          }
          if (!res.ok) {
            console.error('[VideoCapture] Face scan request failed:', res.status, data);
            throw new Error(data?.message || res.statusText);
          }
          console.log('[VideoCapture] Scan result:', data);

          if (mode === 'visitor') {
            if (data.success) {
              setVerification({
                status: 'verified',
                message: data.message || '✅ Visitor photo captured',
                accessGranted: false
              });
              setScanningEnabled(false);
              // Alert removed - no popup for visitor photo capture
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
            console.warn('[VideoCapture] Face not recognized. Response payload:', data);
            setVerification({
              status: 'failed',
              message: 'Face not recognized',
              accessGranted: false
            });
          }
        } catch (err) {
          console.error('[VideoCapture] Verification error:', err);
          setVerification({
            status: 'failed',
            message: (err as Error)?.message || 'Network error',
            accessGranted: false
          });
        }
      }, "image/jpeg");
    } catch (error) {
      console.error('[VideoCapture] scanFace unexpected error:', error);
      setVerification({
        status: 'failed',
        message: 'Scan failed',
        accessGranted: false
      });
    }
  };

  // Manual capture for visitor mode
  const captureVisitorNow = async () => {
    if (mode !== 'visitor') return;
    // Temporarily trigger a scan once
    await scanFace(true);
  };

  // Manual mode selection helpers
  const setEmployeeMode = () => {
    console.log('[VideoCapture] Manually switching to employee mode');
    setMode('employee');
    setScanningEnabled(true);
    setVerification({ status: 'idle', message: 'Face recognition enabled - ready to scan', accessGranted: false });
    setTimeout(() => {
      scanFace(true);
    }, 500);
  };
  const setVisitorMode = () => {
    console.log('[VideoCapture] Manually switching to visitor mode');
    setMode('visitor');
    setScanningEnabled(false);
    setShowVisitorInfoForm(true);
    setVerification({ status: 'idle', message: 'Please fill visitor details to proceed', accessGranted: false });
  };
  const setIdleMode = () => {
    console.log('[VideoCapture] Manually switching to idle mode');
    setMode('idle');
    setScanningEnabled(false);
    setVerification({ status: 'idle', message: 'Waiting for employee classification...', accessGranted: false });
  };

  // Manual verification function
  const handleManualVerification = async () => {
    if (!manualName || !manualEmpId) {
      alert('Please provide both name and employee ID');
      return;
    }

    try {
      const response = await fetch(`${backendBase}/employee_verify`, {
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

      {/* Manual mode controls */}
      <div className="mb-3 flex gap-2">
        <button onClick={setEmployeeMode} className={`px-3 py-2 rounded ${mode==='employee' ? 'bg-blue-700' : 'bg-blue-600 hover:bg-blue-700'}`}>Employee Mode</button>
        <button onClick={setVisitorMode} className={`px-3 py-2 rounded ${mode==='visitor' ? 'bg-indigo-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>Visitor Mode</button>
        <button onClick={setIdleMode} className={`px-3 py-2 rounded ${mode==='idle' ? 'bg-gray-700' : 'bg-gray-600 hover:bg-gray-700'}`}>Idle</button>
      </div>

      {/* Status Display */}
      <div className={`flex items-center mb-3 ${getStatusColor()}`}>
        <span className="mr-2 text-xl">{getStatusIcon()}</span>
        <span className="text-sm">{verification.message}</span>
      </div>

      {/* Visitor info and manual capture */}
      {mode === 'visitor' && (
        <div className="mb-3 space-y-2">
          {showVisitorInfoForm ? (
            <div className="space-y-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={vName}
                  onChange={(e) => setVName(e.target.value)}
                  className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
                />
                <input
                  type="tel"
                  placeholder="Phone"
                  value={vPhone}
                  onChange={(e) => setVPhone(e.target.value)}
                  className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
                />
                <input
                  type="text"
                  placeholder="Purpose (e.g., Interview/Meeting)"
                  value={vPurpose}
                  onChange={(e) => setVPurpose(e.target.value)}
                  className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white md:col-span-2"
                />
                <input
                  type="text"
                  placeholder="Meeting Employee"
                  value={vHost}
                  onChange={(e) => setVHost(e.target.value)}
                  className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white md:col-span-2"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    if (!vName || !vPhone || !vPurpose || !vHost) {
                      alert('Please fill all fields');
                      return;
                    }
                    try {
                      const res = await fetch(`${backendBase}/flow/visitor_info`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: vName, phone: vPhone, purpose: vPurpose, host_employee: vHost })
                      });
                      const data = await res.json();
                      if (!res.ok || data?.success === false) {
                        throw new Error(data?.message || res.statusText);
                      }
                      setVisitorName(vName);
                      setShowVisitorInfoForm(false);
                      setVerification({ status: 'idle', message: 'Info submitted. Preparing photo capture...', accessGranted: false });
                      // The backend will signal start_visitor_photo next; our polling will enable scanning
                    } catch (e: any) {
                      alert(`Failed to submit info: ${e?.message || e}`);
                    }
                  }}
                  className="px-4 py-2 bg-emerald-600 rounded hover:bg-emerald-700"
                >
                  Submit Info
                </button>
              </div>
            </div>
          ) : (
            <>
              <input
                type="text"
                placeholder="Visitor name (optional)"
                value={visitorName}
                onChange={(e) => setVisitorName(e.target.value)}
                className="w-full p-2 bg-gray-700 rounded border border-gray-600 text-white"
              />
              <div className="flex gap-2">
                <button
                  onClick={captureVisitorNow}
                  className="px-4 py-2 bg-indigo-600 rounded hover:bg-indigo-700"
                  disabled={verification.status === 'scanning'}
                >
                  {verification.status === 'scanning' ? 'Capturing...' : 'Capture Now'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

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
