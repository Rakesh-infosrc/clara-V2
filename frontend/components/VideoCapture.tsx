'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRobotExpression } from '@/components/robot/RobotExpressionContext';
import type { Expression } from '@/components/robot/robo-face/expressions';
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

interface SignalPayload {
  expression?: string;
  expr?: string;
  durationMs?: number | string;
  duration?: number | string;
  timeoutMs?: number | string;
  timeout?: number | string;
  message?: string;
}

interface AgentSignal {
  name?: string;
  payload?: SignalPayload | null;
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
  const { triggerExpression } = useRobotExpression();
  const safeTriggerExpression = useCallback(
    (expression: Expression, duration: number) => {
      try {
        triggerExpression(expression, duration);
      } catch (error) {
        console.warn('[VideoCapture] triggerExpression error:', error);
      }
    },
    [triggerExpression]
  );

  // Manual verification state
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualEmpId, setManualEmpId] = useState('');
  const [manualOtp, setManualOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  const faceScanAttemptsRef = useRef(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxFaceScanAttempts = 3;

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
            // Face verification done -> success expression
            safeTriggerExpression('success', 4000);

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
            // Face verification fail -> error expression
            safeTriggerExpression('error', 3000);
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
          safeTriggerExpression('error', 3000);
        }
      } catch (error) {
        console.error('[VideoCapture] scanFace unexpected error:', error);
        setVerification({
          status: 'failed',
          message: 'Scan failed',
          accessGranted: false,
        });
        safeTriggerExpression('error', 3000);
      }
    },
    [backendBase, mode, onVerified, safeTriggerExpression, scanningEnabled, verification.status]
  );

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

  const setVisitorMode = useCallback((instruction?: string) => {
    console.log('[VideoCapture] Switching to visitor mode');
    faceScanAttemptsRef.current = 0;
    setMode('visitor');
    setScanningEnabled(false);
    setVerification({
      status: 'idle',
      message: instruction || 'Visitor mode active. Please wait for assistance.',
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
        safeTriggerExpression('error', 3000);
      });
  }, [safeTriggerExpression]);

  useEffect(() => {
    const checkSignal = async () => {
      try {
        console.log('[VideoCapture] Polling signal endpoint...');
        const response = await fetch(`${backendBase}/get_signal`);
        if (response.ok) {
          const signal = (await response.json()) as AgentSignal;
          console.log('[VideoCapture] Received signal:', signal);
          const payload: SignalPayload = signal.payload ?? {};
          const toExpr = (value: unknown): Expression | null => {
            if (!value || typeof value !== 'string') return null;
            const v = value.toLowerCase();
            const map: Record<string, Expression> = {
              neutral: 'neutral',
              happy: 'happy',
              angry: 'angry',
              sleep: 'sleep',
              thinking: 'thinking',
              listening: 'listening',
              surprised: 'surprised',
              sad: 'sad',
              excited: 'excited',
              confused: 'confused',
              loving: 'loving',
              processing: 'processing',
              error: 'error',
              success: 'success',
            };
            return map[v] ?? null;
          };
          const getDuration = (p: SignalPayload): number | undefined => {
            const d = p?.durationMs ?? p?.duration ?? p?.timeoutMs ?? p?.timeout;
            const n = typeof d === 'number' ? d : typeof d === 'string' ? parseInt(d, 10) : NaN;
            return Number.isNaN(n) ? undefined : n;
          };
          if (signal?.name === 'start_face_capture') {
            console.log('[VideoCapture] Activating employee face capture mode');
            setEmployeeMode();
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (
            signal?.name === 'face_verification_done' ||
            signal?.name === 'face_verified' ||
            signal?.name === 'verification_success'
          ) {
            safeTriggerExpression('success', 4000);
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (
            signal?.name === 'face_verification_fail' ||
            signal?.name === 'face_verification_failed'
          ) {
            safeTriggerExpression('error', 4000);
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'error') {
            safeTriggerExpression('error', 3000);
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (
            signal?.name === 'set_expression' ||
            signal?.name === 'set_expr' ||
            signal?.name === 'expression' ||
            signal?.name === 'expr' ||
            // allow direct expression names as the signal name
            toExpr(signal?.name) !== null
          ) {
            const expr = toExpr(payload.expression ?? payload.expr ?? signal?.name);
            const dur = getDuration(payload) ?? 3000;
            if (expr) {
              safeTriggerExpression(expr, dur);
              await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
            }
          } else if (signal?.name === 'stop_face_capture') {
            console.log('[VideoCapture] Received stop_face_capture signal');
            setIdleMode();
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'start_visitor_info') {
            console.log('[VideoCapture] Switching to visitor info collection mode');
            setVisitorMode(
              signal.payload?.message || 'Visitor mode active. Please wait for assistance.'
            );
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
          } else if (signal?.name === 'start_visitor_photo') {
            console.log('[VideoCapture] Activating visitor photo capture mode');
            setVisitorMode(
              signal.payload?.message || 'Visitor mode active. Please wait for assistance.'
            );
            await fetch(`${backendBase}/clear_signal`, { method: 'POST' });
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
    mode,
    safeTriggerExpression,
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
    <div className="face-card w-[220px] rounded-3xl border border-white/10 bg-blue-800 bg-gradient-to-br from-slate-950/90 via-slate-900/70 to-slate-900/40 p-4 text-white shadow-[0_18px_36px_-18px_rgba(15,23,42,0.75)] backdrop-blur-2xl sm:w-[260px] md:w-[280px]">
      <div className="mb-3 flex flex-col items-center text-center">
        <h3 className="mb-2 text-base font-semibold tracking-wide text-white/90">
          Face Recognition
        </h3>
        <div className="relative w-full overflow-hidden rounded-[18px] border border-white/15 bg-white/5 shadow-[0_14px_30px_-16px_rgba(37,99,235,0.5)]">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/15 via-transparent to-sky-400/15 opacity-55" />
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="face-card__video relative z-[1] h-40 w-full object-cover md:h-48"
          />
        </div>
      </div>

      {/* Manual mode controls */}
      <div className="mb-3 flex justify-center">
        <button
          onClick={setEmployeeMode}
          className={`relative overflow-hidden rounded-xl border border-white/20 px-3 py-2 text-xs font-medium tracking-wide text-white uppercase shadow-lg backdrop-blur-md transition-all duration-300 ease-out ${
            mode === 'employee'
              ? 'border-blue-400/30 bg-gradient-to-r from-blue-500/80 to-blue-600/80 shadow-blue-500/25'
              : 'bg-gradient-to-r from-blue-500/60 to-blue-600/60 hover:border-blue-400/30 hover:from-blue-500/80 hover:to-blue-600/80 hover:shadow-blue-500/25'
          } before:absolute before:inset-0 before:bg-gradient-to-r before:from-white/10 before:to-transparent before:opacity-0 before:transition-opacity before:duration-300 hover:before:opacity-100`}
        >
          <span className="relative z-10">Employee Mode</span>
        </button>
      </div>

      {/* Status Display */}
      <div
        className={`mb-2.5 flex items-center gap-1.5 rounded-2xl border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11px] ${getStatusColor()}`}
      >
        <span className="text-base">{getStatusIcon()}</span>
        <span className="leading-tight text-white/80">{verification.message}</span>
      </div>

      {/* Access Status */}
      <div className="space-y-2">
        {verification.accessGranted && (
          <div className="rounded-2xl border border-green-400/60 bg-green-500/25 p-2.5 text-[11px] shadow-[0_14px_24px_-18px_rgba(34,197,94,0.4)]">
            <p className="text-green-300/90">🔓 Full Access Granted</p>
            {verification.employeeName && (
              <p className="text-xs font-semibold text-green-100">
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
