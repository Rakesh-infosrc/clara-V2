'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { motion } from 'motion/react';
import { RoomAudioRenderer, RoomContext, StartAudio, useChat } from '@livekit/components-react';
import VideoCapture from '@/components/VideoCapture';
import { toastAlert } from '@/components/alert-toast';
import AnimatedBackground from '@/components/animated-background';
import { RobotExpressionProvider } from '@/components/robot/RobotExpressionContext';
import { SessionView } from '@/components/session-view';
import { Toaster } from '@/components/ui/sonner';
import { Welcome } from '@/components/welcome';
import type { AppConfig } from '@/lib/types';
import { BACKEND_BASE_URL } from '@/lib/utils';

const MotionWelcome = motion.create(Welcome);
const MotionSessionView = motion.create(SessionView);

interface AppProps {
  appConfig: AppConfig;
}

function FaceCaptureDock() {
  const chat = useChat();

  const handleVerified = useCallback(
    (employeeName?: string, employeeId?: string, agentMessage?: string) => {
      const displayName =
        employeeName && employeeName.trim().length > 0 ? employeeName.trim() : 'there';
      const trimmedAgentMessage = agentMessage?.trim();

      const directiveParts: string[] = [
        '[[sys:face_verified]] Face recognition completed.',
        `Employee: ${displayName}${employeeId ? ` (${employeeId})` : ''}.`,
      ];

      if (trimmedAgentMessage && trimmedAgentMessage.length > 0) {
        directiveParts.push(`Suggested greeting: ${trimmedAgentMessage}`);
      } else {
        directiveParts.push(
          'Please greet the employee, confirm their full access, and offer further assistance.'
        );
      }

      const directive = directiveParts.join(' ');

      chat.send(directive).catch((err) => {
        console.error('[FaceCaptureDock] Failed to send verification message to agent:', err);
      });
    },
    [chat]
  );

  return (
    <motion.div
      drag
      dragMomentum={false}
      dragElastic={0.12}
      className="pointer-events-auto fixed right-4 bottom-4 left-4 z-50 mx-auto w-auto max-w-md rounded-[30px] bg-blue-950 shadow-lg sm:right-6 sm:left-auto sm:max-w-[320px] md:top-auto md:right-8 md:bottom-20 md:left-auto md:translate-y-0 xl:top-1/2 xl:right-10 xl:bottom-auto xl:left-auto xl:-translate-y-1/2"
    >
      <VideoCapture onVerified={handleVerified} />
    </motion.div>
  );
}

export function App({ appConfig }: AppProps) {
  const room = useMemo(() => new Room(), []);
  const [sessionStarted, setSessionStarted] = useState(false);
  const roomNameRef = useRef<string | null>(null);

  // ✅ Fetch token + URL from FastAPI backend
  const backendBase = BACKEND_BASE_URL;
  const createRoomSession = useCallback(
    async (identity: string) => {
      const roomName = `Clara-room-${Date.now()}`;

      const tokenResp = await fetch(
        `${backendBase}/get-token?identity=${encodeURIComponent(identity)}&room=${encodeURIComponent(roomName)}`
      );
      console.log('createRoomSession/get-token', {
        roomName,
        identity,
        status: tokenResp.status,
      });
      if (!tokenResp.ok) {
        throw new Error(`Failed to fetch token: ${tokenResp.status}`);
      }
      const tokenData = await tokenResp.json();

      const dispatchResp = await fetch(`${backendBase}/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room: roomName,
          agent_name: appConfig.agentName || 'clara-receptionist',
        }),
      });
      console.log('createRoomSession/dispatch', {
        roomName,
        status: dispatchResp.status,
      });

      if (!dispatchResp.ok) {
        throw new Error(`Failed to dispatch agent: ${dispatchResp.status}`);
      }

      return {
        serverUrl: tokenData.url,
        participantToken: tokenData.token,
        roomName,
      };
    },
    [appConfig.agentName, backendBase]
  );

  useEffect(() => {
    const onDisconnected = () => {
      setSessionStarted(false);
    };

    const onMediaDevicesError = (error: Error) => {
      toastAlert({
        title: 'Encountered an error with your media devices',
        description: `${error.name}: ${error.message}`,
      });
    };

    room.on(RoomEvent.MediaDevicesError, onMediaDevicesError);
    room.on(RoomEvent.Disconnected, onDisconnected);

    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      room.off(RoomEvent.MediaDevicesError, onMediaDevicesError);
    };
  }, [room]);

  useEffect(() => {
    let aborted = false;

    const startSession = async () => {
      // 1️⃣ Generate a unique identity per session
      const identity = `frontend-user_${Math.floor(Math.random() * 10000)}`;

      try {
        // 2️⃣ Disconnect previous session if it exists
        if (room.state !== 'disconnected') {
          await room.disconnect();
          // Small delay to ensure LiveKit server cleans up
          await new Promise((res) => setTimeout(res, 500));
        }

        if (roomNameRef.current) {
          const previousRoom = roomNameRef.current;
          roomNameRef.current = null;
          try {
            await fetch(`${backendBase}/flow/end`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ room: previousRoom }),
            });
          } catch (cleanupErr) {
            console.warn('Failed to clean up previous room', previousRoom, cleanupErr);
          }
        }

        // 3️⃣ Fetch new token & dispatch agent for dedicated room
        const connectionDetails = await createRoomSession(identity);
        const activeRoom = connectionDetails.roomName;
        roomNameRef.current = activeRoom;

        // 4️⃣ Connect to LiveKit
        await room.connect(connectionDetails.serverUrl, connectionDetails.participantToken);

        // 5️⃣ Enable microphone after connection
        await room.localParticipant.setMicrophoneEnabled(true, undefined, {
          preConnectBuffer: appConfig.isPreConnectBufferEnabled,
        });

        if (!aborted) setSessionStarted(true);
      } catch (error: unknown) {
        if (aborted) return;
        const err = error instanceof Error ? error : new Error('Unknown LiveKit connection error');
        toastAlert({
          title: 'Error connecting to LiveKit',
          description: `${err.name}: ${err.message}`,
        });
      }
    };

    if (sessionStarted) {
      startSession();
    }

    return () => {
      aborted = true;
      room.disconnect().catch(() => {});
      const roomToClose = roomNameRef.current;
      roomNameRef.current = null;
      if (roomToClose) {
        fetch(`${backendBase}/flow/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room: roomToClose }),
        }).catch(() => {});
      }
    };
  }, [sessionStarted, room, appConfig.isPreConnectBufferEnabled, backendBase, createRoomSession]);

  const { startButtonText } = appConfig;

  return (
    <main className="relative min-h-screen overflow-hidden">
      <AnimatedBackground />
      <div className="relative z-10 flex min-h-screen flex-col">
        <MotionWelcome
          key="welcome"
          startButtonText={startButtonText}
          onStartCall={() => setSessionStarted(true)}
          disabled={sessionStarted}
          initial={{ opacity: 1 }}
          animate={{ opacity: sessionStarted ? 0 : 1 }}
          transition={{
            duration: 0.5,
            ease: 'linear',
            delay: sessionStarted ? 0 : 0.5,
          }}
        />

        <RoomContext.Provider value={room}>
          <RobotExpressionProvider>
            <RoomAudioRenderer />
            <StartAudio label="Start Audio" />

            <MotionSessionView
              key="session-view"
              appConfig={appConfig}
              disabled={!sessionStarted}
              sessionStarted={sessionStarted}
              initial={{ opacity: 0 }}
              animate={{ opacity: sessionStarted ? 1 : 0 }}
              transition={{
                duration: 0.5,
                ease: 'linear',
                delay: sessionStarted ? 0.5 : 0,
              }}
            />

            {/* 👇 Face Recognition UI with automatic agent greeting */}
            {sessionStarted && <FaceCaptureDock />}
          </RobotExpressionProvider>
        </RoomContext.Provider>

        <Toaster />
      </div>
    </main>
  );
}
