import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { VideoTrack } from '@livekit/components-react';
import { cn } from '@/lib/utils';

const MotionVideoTrack = motion.create(VideoTrack);

interface VideoTileProps extends React.ComponentProps<'div'> {
  trackRef?: React.RefObject<VideoTrack> | any;
}

interface VerificationState {
  status: 'idle' | 'scanning' | 'verified' | 'failed';
  message: string;
  employeeName?: string;
}

export const VideoTile: React.FC<VideoTileProps> = ({ trackRef, className, ref }) => {
  const [verification, setVerification] = useState<VerificationState>({
    status: 'idle',
    message: ''
  });
  const verificationInProgress = useRef(false);
  const scanCount = useRef(0);
  const maxScans = 5; // Limit automatic scanning attempts

  const verifyFace = async () => {
    if (!trackRef || verificationInProgress.current || verification.status === 'verified') {
      return;
    }

    const videoEl = trackRef?.attachedElements?.[0] as HTMLVideoElement;
    if (!videoEl || videoEl.videoWidth === 0 || videoEl.videoHeight === 0) {
      return;
    }

    // Stop after max attempts
    if (scanCount.current >= maxScans) {
      setVerification({
        status: 'failed',
        message: 'Auto-scan stopped. Use manual verification if needed.'
      });
      return;
    }

    verificationInProgress.current = true;
    scanCount.current++;
    
    setVerification({
      status: 'scanning',
      message: `Scanning face... (${scanCount.current}/${maxScans})`
    });

    try {
      const canvas = document.createElement("canvas");
      canvas.width = videoEl.videoWidth;
      canvas.height = videoEl.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

      // Convert to blob and send to face_login endpoint
      canvas.toBlob(async (blob) => {
        if (!blob) return;
        const formData = new FormData();
        formData.append("image", blob, "frame.jpg");

        try {
          const res = await fetch("http://127.0.0.1:8000/face_login", {
            method: "POST",
            body: formData,
          });

          const data = await res.json();
          console.log("Face verification result:", data);

          if (data.success && data.verified) {
            setVerification({
              status: 'verified',
              message: 'Face verified! ✅',
              employeeName: data.employeeName
            });
            
            // Show success notification
            console.log(`🎉 ${data.message}`);
          } else {
            if (scanCount.current >= maxScans) {
              setVerification({
                status: 'failed',
                message: 'Face not recognized. Manual verification available.'
              });
            } else {
              setVerification({
                status: 'idle',
                message: 'Face not recognized, retrying...'
              });
            }
          }
        } catch (err) {
          console.error("Face verification failed:", err);
          setVerification({
            status: 'failed',
            message: 'Network error during verification'
          });
        } finally {
          verificationInProgress.current = false;
        }
      }, "image/jpeg", 0.8);
    } catch (error) {
      console.error("Canvas error:", error);
      setVerification({
        status: 'failed',
        message: 'Failed to capture image'
      });
      verificationInProgress.current = false;
    }
  };

  // Auto-verify every 4 seconds until verified or max attempts reached
  useEffect(() => {
    if (verification.status === 'verified' || scanCount.current >= maxScans) {
      return;
    }

    const interval = setInterval(() => {
      verifyFace();
    }, 4000);

    return () => clearInterval(interval);
  }, [trackRef, verification.status]);

  // Get status indicator color
  const getStatusColor = () => {
    switch (verification.status) {
      case 'verified': return 'border-green-500';
      case 'scanning': return 'border-yellow-500';
      case 'failed': return 'border-red-500';
      default: return 'border-gray-500';
    }
  };

  return (
    <div ref={ref} className={cn('bg-muted overflow-hidden rounded-md relative', className, getStatusColor(), 'border-2')}>
      <MotionVideoTrack
        trackRef={trackRef}
        width={trackRef?.publication?.dimensions?.width ?? 0}
        height={trackRef?.publication?.dimensions?.height ?? 0}
        className={cn('h-full w-auto')}
      />
      
      {/* Verification Status Overlay */}
      {verification.message && (
        <div className={cn(
          'absolute top-2 left-2 right-2 px-2 py-1 rounded text-xs font-medium text-white',
          verification.status === 'verified' && 'bg-green-600',
          verification.status === 'scanning' && 'bg-yellow-600',
          verification.status === 'failed' && 'bg-red-600',
          verification.status === 'idle' && 'bg-gray-600'
        )}>
          {verification.message}
        </div>
      )}
      
      {/* Employee Name Display */}
      {verification.status === 'verified' && verification.employeeName && (
        <div className="absolute bottom-2 left-2 right-2 px-2 py-1 bg-green-600 rounded text-xs font-medium text-white text-center">
          Welcome, {verification.employeeName}!
        </div>
      )}
    </div>
  );
};
