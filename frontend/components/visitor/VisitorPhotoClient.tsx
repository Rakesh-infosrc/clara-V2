'use client';

import React, { useEffect, useState } from 'react';
import { Room } from 'livekit-client';
import { RoomContext } from '@livekit/components-react';
import VideoCapture from '@/components/VideoCapture';
import { RobotExpressionProvider } from '@/components/robot/RobotExpressionContext';

export default function VisitorPhotoClient() {
  const [room, setRoom] = useState<Room | null>(null);

  useEffect(() => {
    const r = new Room();
    setRoom(r);
    return () => {
      r.disconnect().catch(() => {});
    };
  }, []);

  if (!room) return null;

  return (
    <RoomContext.Provider value={room}>
      <RobotExpressionProvider>
        <VideoCapture />
      </RobotExpressionProvider>
    </RoomContext.Provider>
  );
}
