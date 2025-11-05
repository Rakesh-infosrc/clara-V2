'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { BACKEND_BASE_URL } from '@/lib/utils';

type FaceFlowState =
  | 'idle'
  | 'face_recognition'
  | 'visitor_info_collection'
  | 'flow_end'
  | string
  | null;

interface FaceResultPayload {
  status?: string;
  name?: string;
  employeeId?: string;
  employeeName?: string;
}

interface FaceFlowResponse {
  success: boolean;
  message?: string;
  next_state?: FaceFlowState;
  face_result?: FaceResultPayload;
  flow_status?: {
    current_state?: FaceFlowState;
  } | null;
}

interface VerificationState {
  status: 'scanning' | 'verified' | 'failed' | 'manual_input' | 'idle';
  message: string;
  employeeName?: string;
  employeeId?: string;
  accessGranted: boolean;
}

const drawFrameToCanvas = (video: HTMLVideoElement) => {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas;
};

const canvasToBlob = async (canvas: HTMLCanvasElement, type: string) => {
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((result) => resolve(result), type);
  });
  if (!blob) {
    throw new Error('Unable to capture photo.');
  }
  return blob;
};

interface VideoCaptureProps {
  onVerified?: (employeeName?: string, employeeId?: string, agentMessage?: string) => void;
}

export default function VideoCapture({ onVerified }: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [verification, setVerification] = useState<VerificationState>({
    status: 'idle',
    message: 'Waiting for employee classification...',
    accessGranted: false,
  });
  const [scanningEnabled, setScanningEnabled] = useState(false);
  const [mode, setMode] = useState<'idle' | 'employee' | 'visitor'>('idle');
  const backendBase = typeof window !== 'undefined' ? BACKEND_BASE_URL : '';

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

  const faceScanAttemptsRef = useRef(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxFaceScanAttempts = 3;

  const captureVisitorPhoto = useCallback(
    async (autoCapture: boolean = false, overrideMessage?: string) => {
      if (!autoCapture && mode !== 'visitor') {
        return;
      }

      const video = videoRef.current;
      if (!video) {
        return;
      }

      const stream = video.srcObject as MediaStream | null;
      const track = stream?.getVideoTracks?.()[0];
      const isLive = !!track && track.readyState === 'live' && video.videoWidth > 0;
      if (!isLive) {
        console.warn('[VideoCapture] Camera feed not live for visitor capture.');
        setVerification({
          status: 'failed',
          message: 'Camera feed not available. Please turn your camera on.',
          accessGranted: false,
        });
        if (track && track.readyState !== 'live') {
          track.stop();
        }
        return;
      }

      const statusMessage = overrideMessage?.trim()?.length
        ? overrideMessage
        : autoCapture
          ? 'Capturing visitor photo...'
          : 'Capturing photo...';

      setVerification((prev) => ({
        ...prev,
        status: 'scanning',
        message: statusMessage,
      }));

      try {
        const canvas = drawFrameToCanvas(video);
        const blob = await canvasToBlob(canvas, 'image/jpeg');

        const formData = new FormData();
        formData.append('image', blob, 'visitor.jpg');
        const submittedName = (visitorName || vName).trim();
        if (submittedName) {
          formData.append('visitor_name', submittedName);
        }

        const response = await fetch(`${backendBase}/flow/visitor_photo`, {
          method: 'POST',
          body: formData,
        });

        let data: FaceFlowResponse | null = null;
        try {
          data = (await response.json()) as FaceFlowResponse;
        } catch {
          // ignore JSON parse errors
        }

        if (!response.ok) {
          const errorMessage = data?.message ?? response.statusText;
          console.error(
            '[VideoCapture] Visitor photo capture failed:',
            response.status,
            errorMessage
          );
          throw new Error(errorMessage);
        }

        if (data?.success) {
          setVerification({
            status: 'verified',
            message: data.message || '✅ Visitor photo captured',
            accessGranted: false,
          });
        } else {
          setVerification({
            status: 'failed',
            message: data?.message || 'Visitor photo failed',
            accessGranted: false,
          });
        }
      } catch (error) {
        console.error('[VideoCapture] captureVisitorPhoto unexpected error:', error);
        setVerification({
          status: 'failed',
          message: 'Capture failed',
          accessGranted: false,
        });
      }
    },
    [backendBase, mode, vName, visitorName]
  );

  const scanFace = useCallback(
    async (force: boolean = false) => {
      console.log(
        '[VideoCapture] scanFace invoked. Mode:',
        mode,
        'Status:',
        verification.status,
        'Scanning enabled:',
        scanningEnabled
      );

      if (mode === 'visitor') {
        if (force) {
          await captureVisitorPhoto(true);
        }
        return;
      }

      const video = videoRef.current;
      if (!video || (!scanningEnabled && !force) || verification.status === 'verified') {
        return;
      }

      const stream = video.srcObject as MediaStream | null;
      const track = stream?.getVideoTracks?.()[0];
      const isLive = !!track && track.readyState === 'live' && video.videoWidth > 0;
      if (!isLive) {
        console.warn(
          '[VideoCapture] Camera feed not live. Track status:',
          track?.readyState,
          'videoWidth:',
          video.videoWidth
        );
        setVerification((prev) => ({
          ...prev,
          status: 'idle',
          message: 'Initializing camera...',
          accessGranted: false,
        }));
        if (force) {
          setTimeout(() => {
            void scanFace(true);
          }, 800);
        }
        return;
      }

      setVerification((prev) => ({ ...prev, status: 'scanning', message: 'Scanning face...' }));

      try {
        const canvas = drawFrameToCanvas(video);
        const blob = await canvasToBlob(canvas, 'image/jpeg');
        const formData = new FormData();
        formData.append('image', blob, 'frame.jpg');

        try {
          const endpoint = `${backendBase}/flow/face_recognition`;
          console.log('[VideoCapture] Submitting frame to endpoint:', endpoint);
          const response = await fetch(endpoint, {
            method: 'POST',
            body: formData,
          });

          let data: FaceFlowResponse | null = null;
          try {
            data = (await response.json()) as FaceFlowResponse;
          } catch {
            // ignore JSON parse errors
          }

          if (!response.ok) {
            const errorMessage = data?.message ?? response.statusText;
            console.error(
              '[VideoCapture] Face scan request failed:',
              response.status,
              errorMessage
            );
            throw new Error(errorMessage);
          }

          if (data?.success && data.face_result?.status === 'success') {
            faceScanAttemptsRef.current = 0;
            const empNameRaw = data.face_result?.name || data.face_result?.employeeName;
            const empName = empNameRaw?.trim()?.length ? empNameRaw.trim() : undefined;
            const empId = data.face_result?.employeeId;
            const now = new Date();
            const formattedTime = new Intl.DateTimeFormat(undefined, {
              hour: 'numeric',
              minute: '2-digit',
            }).format(now);
            const greetingName = empName || 'there';
            const successMessage = `${formattedTime} I'm glad to see you, ${greetingName}${empId ? ` (${empId})` : ''}.`;
            const agentGreeting = data.message?.trim();

            setVerification({
              status: 'verified',
              message: 'Face verified successfully.',
              accessGranted: true,
              employeeName: empName || empNameRaw,
              employeeId: empId,
            });
            setScanningEnabled(false);

            if (onVerified) {
              onVerified(empName || empNameRaw, empId, agentGreeting || successMessage);
            }
          } else if (data?.success === false && data.face_result?.status === 'manual_input') {
            faceScanAttemptsRef.current = maxFaceScanAttempts;
            setVerification({
              status: 'manual_input',
              message: 'Face not recognized.',
              accessGranted: false,
            });
            setScanningEnabled(false);
            setShowManualInput(true);
          } else {
            faceScanAttemptsRef.current += 1;
            const shouldRetry = faceScanAttemptsRef.current < maxFaceScanAttempts;
            setVerification({
              status: 'failed',
              message: 'Face not recognized.',
              accessGranted: false,
            });
            if (shouldRetry) {
              setTimeout(() => {
                void scanFace(true);
              }, 1200);
            } else {
              setScanningEnabled(false);
            }
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Network error';
          console.error('[VideoCapture] scanFace network error:', error);
          setVerification({
            status: 'failed',
            message,
            accessGranted: false,
          });
        }
      } catch (error) {
        console.error('[VideoCapture] scanFace unexpected error:', error);
        setVerification({
          status: 'failed',
          message: 'Scan failed',
          accessGranted: false,
        });
      }
    },
    [backendBase, captureVisitorPhoto, mode, onVerified, scanningEnabled, verification.status]
  );

  const captureVisitorNow = useCallback(async () => {
    if (mode !== 'visitor') {
      return;
    }
    await captureVisitorPhoto();
  }, [captureVisitorPhoto, mode]);

  const setEmployeeMode = useCallback(() => {
    console.log('[VideoCapture] Switching to employee mode');
    faceScanAttemptsRef.current = 0;
    setMode('employee');
    setScanningEnabled(true);
    setVerification({
      status: 'idle',
      message: 'Face recognition enabled - ready to scan',
      accessGranted: false,
    });
    setTimeout(() => {
      void scanFace(true);
    }, 500);
  }, [scanFace]);

  const setVisitorMode = useCallback(() => {
    console.log('[VideoCapture] Switching to visitor mode');
    faceScanAttemptsRef.current = 0;
    setMode('visitor');
    setScanningEnabled(false);
    setShowVisitorInfoForm(true);
    setVerification({
      status: 'idle',
      message: 'Please fill visitor details to proceed',
      accessGranted: false,
    });
  }, []);

  const setIdleMode = useCallback(() => {
    console.log('[VideoCapture] Switching to idle mode');
    faceScanAttemptsRef.current = 0;
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setMode('idle');
    setScanningEnabled(false);
    setVerification({
      status: 'idle',
      message: 'Awaiting next visitor...',
      accessGranted: false,
      employeeName: undefined,
      employeeId: undefined,
    });
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (typeof onVerified === 'function') {
      onVerified(undefined, undefined, '');
    }
  }, [onVerified]);

  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => {
        console.error('Camera error:', err);
        setVerification({
          status: 'failed',
          message: 'Camera access denied',
          accessGranted: false,
        });
      });
  }, []);

  useEffect(() => {
    const checkSignal = async () => {
      try {
        console.log('[VideoCapture] Polling signal endpoint...');
        const response = await fetch(`${backendBase}/get_signal`);
        if (response.ok) {
          const signal = await response.json();
          console.log('[VideoCapture] Received signal:', signal);
          if (signal?.name === 'start_face_capture') {
            console.log('[VideoCapture] Activating employee face capture mode');
            setEmployeeMode();
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'stop_face_capture') {
            console.log('[VideoCapture] Received stop_face_capture signal');
            setIdleMode();
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'start_visitor_info') {
            console.log('[VideoCapture] Switching to visitor info collection mode');
            setVisitorMode();
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'start_visitor_photo') {
            console.log('[VideoCapture] Activating visitor photo capture mode');
            setMode('visitor');
            setScanningEnabled(false);
            setVerification({
              status: 'idle',
              message: signal.payload?.message || 'Capturing visitor photo...',
              accessGranted: false,
            });
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
            setTimeout(() => {
              void captureVisitorPhoto(true, signal.payload?.message);
            }, 500);
          }
        }

        // Disabled auto-trigger based on flow state to prevent unwanted face scanning
        // Only rely on explicit signals from backend
        // if (!scanningEnabled) {
        //   try {
        //     const statusResp = await fetch(`${backendBase}/flow/status`);
        //     if (statusResp.ok) {
        //       const statusJson = await statusResp.json();
        //       const backendState = statusJson?.flow_status?.current_state;
        //       if (backendState === 'face_recognition' && mode !== 'employee') {
        //         console.log(
        //           '[VideoCapture] Flow state indicates face recognition; enabling employee mode fallback'
        //         );
        //         setEmployeeMode();
        //       } else if (backendState === 'idle' && mode !== 'idle') {
        //         console.log('[VideoCapture] Flow state indicates idle; switching to idle mode');
        //         setIdleMode();
        //       }
        //     }
        //   } catch (statusErr) {
        //     console.log('[VideoCapture] Flow status polling error:', statusErr);
        //   }
        // }
      } catch (error) {
        console.log('[VideoCapture] Signal polling error:', error);
      }
    };

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    const interval = setInterval(checkSignal, 2000);
    pollingRef.current = interval;

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [
    backendBase,
    captureVisitorPhoto,
    mode,
    scanFace,
    scanningEnabled,
    setEmployeeMode,
    setIdleMode,
    setVisitorMode,
  ]);

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
          otp: otpSent ? manualOtp : undefined,
        }),
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
            employeeName: manualName,
          });
          setShowManualInput(false);
        }
      } else {
        alert(data.message || 'Verification failed');
      }
    } catch (error) {
      console.error('[VideoCapture] Manual verification error:', error);
      alert('Network error during manual verification');
    }
  };

  const getStatusColor = () => {
    switch (verification.status) {
      case 'verified':
        return 'text-green-400';
      case 'scanning':
        return 'text-yellow-400';
      case 'failed':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = () => {
    switch (verification.status) {
      case 'verified':
        return '✅';
      case 'scanning':
        return '🔍';
      case 'failed':
        return '❌';
      default:
        return '👤';
    }
  };

  return (
    <div className="min-w-[300px] rounded-lg bg-gray-900 p-4 text-white shadow-lg">
      <div className="mb-3">
        <h3 className="mb-2 text-lg font-semibold">Face Recognition</h3>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-48 w-full rounded-lg border-2 border-gray-700 object-cover"
        />
      </div>

      {/* Manual mode controls */}
      <div className="mb-3 flex gap-2">
        <button
          onClick={setEmployeeMode}
          className={`rounded px-3 py-2 ${mode === 'employee' ? 'bg-blue-700' : 'bg-blue-600 hover:bg-blue-700'}`}
        >
          Employee Mode
        </button>
        <button
          onClick={setVisitorMode}
          className={`rounded px-3 py-2 ${mode === 'visitor' ? 'bg-indigo-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}
        >
          Visitor Mode
        </button>
        <button
          onClick={setIdleMode}
          className={`rounded px-3 py-2 ${mode === 'idle' ? 'bg-gray-700' : 'bg-gray-600 hover:bg-gray-700'}`}
        >
          Idle
        </button>
      </div>

      {/* Status Display */}
      <div className={`mb-3 flex items-center ${getStatusColor()}`}>
        <span className="mr-2 text-xl">{getStatusIcon()}</span>
        <span className="text-sm">{verification.message}</span>
      </div>

      {/* Visitor info and manual capture */}
      {mode === 'visitor' && (
        <div className="mb-3 space-y-2">
          {showVisitorInfoForm ? (
            <div className="space-y-2">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={vName}
                  onChange={(e) => setVName(e.target.value)}
                  className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
                />
                <input
                  type="tel"
                  placeholder="Phone"
                  value={vPhone}
                  onChange={(e) => setVPhone(e.target.value)}
                  className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
                />
                <input
                  type="text"
                  placeholder="Purpose (e.g., Interview/Meeting)"
                  value={vPurpose}
                  onChange={(e) => setVPurpose(e.target.value)}
                  className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white md:col-span-2"
                />
                <input
                  type="text"
                  placeholder="Meeting Employee"
                  value={vHost}
                  onChange={(e) => setVHost(e.target.value)}
                  className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white md:col-span-2"
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
                        body: JSON.stringify({
                          name: vName,
                          phone: vPhone,
                          purpose: vPurpose,
                          host_employee: vHost,
                        }),
                      });
                      const data = await res.json();
                      if (!res.ok || data?.success === false) {
                        throw new Error(data?.message || res.statusText);
                      }
                      setVisitorName(vName);
                      setShowVisitorInfoForm(false);
                      setVerification({
                        status: 'idle',
                        message: 'Info submitted. Preparing photo capture...',
                        accessGranted: false,
                      });
                      setTimeout(() => {
                        captureVisitorPhoto(true, data?.next_prompt || data?.message);
                      }, 800);
                      // The backend will signal start_visitor_photo next; our polling will enable scanning
                    } catch (error: unknown) {
                      const message = error instanceof Error ? error.message : String(error);
                      console.error('[VideoCapture] Visitor info submission failed:', error);
                      alert(`Failed to submit info: ${message}`);
                    }
                  }}
                  className="rounded bg-emerald-600 px-4 py-2 hover:bg-emerald-700"
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
                className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
              />
              <div className="flex gap-2">
                <button
                  onClick={captureVisitorNow}
                  className="rounded bg-indigo-600 px-4 py-2 hover:bg-indigo-700"
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
          <div className="rounded-lg bg-green-800 p-3">
            <p className="text-sm text-green-200">🔓 Full Access Granted</p>
            {verification.employeeName && (
              <p className="font-semibold text-green-100">
                {verification.employeeName}
                {verification.employeeId ? ` (${verification.employeeId})` : ''}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Manual Input Modal */}
      {showManualInput && (
        <div className="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black">
          <div className="w-96 rounded-lg bg-gray-800 p-6">
            <h3 className="mb-4 text-lg font-semibold">Manual Verification</h3>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="Full Name"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
              />

              <input
                type="text"
                placeholder="Employee ID"
                value={manualEmpId}
                onChange={(e) => setManualEmpId(e.target.value)}
                className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
              />

              {otpSent && (
                <input
                  type="text"
                  placeholder="Enter OTP"
                  value={manualOtp}
                  onChange={(e) => setManualOtp(e.target.value)}
                  className="w-full rounded border border-gray-600 bg-gray-700 p-2 text-white"
                />
              )}
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={handleManualVerification}
                className="flex-1 rounded bg-blue-600 px-4 py-2 hover:bg-blue-700"
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
                className="flex-1 rounded bg-gray-600 px-4 py-2 hover:bg-gray-700"
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
