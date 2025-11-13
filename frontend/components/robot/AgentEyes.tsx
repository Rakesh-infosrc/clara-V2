'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { type AgentState, useVoiceAssistant } from '@livekit/components-react';
import { cn } from '@/lib/utils';
import EyeScene from './RobotEye3D';

// Keep this type aligned with RobotEye3D's supported emotions
// (duplicated here to avoid changing the original file's exports)
type EmotionKey = 'neutral' | 'happy' | 'angry' | 'sleep' | 'thinking' | 'listening' | 'surprised';

function stateToEmotion(state: AgentState): EmotionKey {
  switch (state) {
    case 'connecting':
      return 'surprised';
    case 'listening':
      return 'listening';
    case 'thinking':
      return 'thinking';
    case 'speaking':
      return 'happy'; // treat speaking as lively/happy
    default:
      return 'neutral';
  }
}

interface AgentEyesProps {
  className?: string;
  eyes?: number;
}

export function AgentEyes({ className, eyes = 2 }: AgentEyesProps) {
  const { state, audioTrack } = useVoiceAssistant();
  const [energy, setEnergy] = useState(0);
  const [isHidden, setIsHidden] = useState(false);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  useEffect(() => {
    const onVis = () =>
      setIsHidden(typeof document !== 'undefined' && document.visibilityState !== 'visible');
    onVis();
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, []);

  useEffect(() => {
    // Cleanup helper
    const cleanup = () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;

      try {
        sourceRef.current?.disconnect();
      } catch {
        /* noop */
      }

      try {
        analyserRef.current?.disconnect();
      } catch {
        /* noop */
      }

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

    // Build a stream from the agent's remote audio MediaStreamTrack
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
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        // When tab hidden, decay energy and skip heavy work
        setEnergy((prev) => prev * 0.9);
      } else {
        analyser.getByteFrequencyData(data);
        // Compute normalized energy 0..1
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        const avg = sum / (data.length * 255);
        // Ease slightly for stability
        setEnergy((prev) => prev * 0.8 + avg * 0.2);
      }
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);

    return cleanup;
  }, [audioTrack?.publication?.track]);

  const emotion = useMemo<EmotionKey>(() => {
    const base = stateToEmotion(state);
    const active =
      state === 'connecting' ||
      state === 'listening' ||
      state === 'thinking' ||
      state === 'speaking';
    return active ? base : 'sleep';
  }, [state]);

  const dim = useMemo(() => {
    if (isHidden) return 0.5;
    return emotion === 'sleep' ? 0.75 : 1;
  }, [isHidden, emotion]);

  return (
    <div className={cn('relative min-h-[90px] w-full', className)}>
      <div className="absolute inset-0">
        <EyeScene emotion={emotion} eyes={eyes} energy={energy} dim={dim} />
      </div>
    </div>
  );
}

export default AgentEyes;
