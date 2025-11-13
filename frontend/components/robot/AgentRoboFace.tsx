'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useVoiceAssistant } from '@livekit/components-react';
import { cn } from '@/lib/utils';
import { useRobotExpression } from './RobotExpressionContext';
import RoboFaceComponent from './robo-face/RoboFace';

export default function AgentRoboFace({ className }: { className?: string }) {
  const { expression } = useRobotExpression();
  const { audioTrack } = useVoiceAssistant();
  const [energy, setEnergy] = useState(0);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  useEffect(() => {
    const cleanup = () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      try {
        sourceRef.current?.disconnect();
      } catch {}
      try {
        analyserRef.current?.disconnect();
      } catch {}
      sourceRef.current = null;
      analyserRef.current = null;
      void audioCtxRef.current?.close();
      audioCtxRef.current = null;
    };

    if (!audioTrack?.publication?.track) {
      cleanup();
      setEnergy(0);
      return;
    }

    const mediaStreamTrack: MediaStreamTrack | undefined = (
      audioTrack.publication.track as { mediaStreamTrack?: MediaStreamTrack } | undefined
    )?.mediaStreamTrack;
    if (!mediaStreamTrack) {
      cleanup();
      setEnergy(0);
      return;
    }

    const AudioCtor: typeof AudioContext | undefined =
      typeof window !== 'undefined'
        ? (window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext)
        : undefined;
    if (!AudioCtor) {
      cleanup();
      setEnergy(0);
      return;
    }
    const ctx = new AudioCtor();
    const stream = new MediaStream([mediaStreamTrack]);
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(analyser);

    audioCtxRef.current = ctx;
    analyserRef.current = analyser;
    sourceRef.current = source;

    const data = new Uint8Array(analyser.frequencyBinCount);
    const loop = () => {
      analyser.getByteFrequencyData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i];
      const avg = sum / (data.length * 255);
      setEnergy((prev) => prev * 0.8 + avg * 0.2);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);

    return cleanup;
  }, [audioTrack?.publication?.track]);
  return (
    <div className={cn('relative flex h-full w-full items-center justify-center', className)}>
      <div className="pointer-events-none">
        <RoboFaceComponent expression={expression} energy={energy} className="max-w-[640px]" />
      </div>
    </div>
  );
}
