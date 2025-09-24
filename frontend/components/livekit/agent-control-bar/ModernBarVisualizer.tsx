import React, { useEffect, useRef, useState } from 'react';
import { animate } from 'animejs';

const BAR_COUNT = 20;
const MAX_BAR_HEIGHT = 100; // percent
const MIN_BAR_HEIGHT = 10; // percent

export default function ModernBarVisualizer() {
  const containerRef = useRef<SVGSVGElement | null>(null);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const barsRef = useRef<(SVGRectElement | null)[]>([]);

  useEffect(() => {
    async function setupAudio() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const context = new AudioContext();
        const source = context.createMediaStreamSource(stream);
        const analyser = context.createAnalyser();
        analyser.fftSize = 64;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        source.connect(analyser);

        analyserRef.current = analyser;
        dataArrayRef.current = dataArray;
        setAudioContext(context);
      } catch (err) {
        console.error('Microphone permission denied or error:', err);
      }
    }
    setupAudio();

    return () => {
      audioContext?.close();
    };
  }, []);

  useEffect(() => {
    if (!audioContext || !analyserRef.current || !barsRef.current.length) return;

    let animationFrameId: number;

    const animateBars = () => {
      const analyser = analyserRef.current!;
      const dataArray = dataArrayRef.current!;
      analyser.getByteFrequencyData(dataArray);

      // Prepare array of bars that actually exist (not null)
      const targets = barsRef.current.filter((bar): bar is SVGRectElement => bar !== null);

      // Limit the frequency data to the number of bars
      const values = Array.from(dataArray).slice(0, BAR_COUNT);

      const heights = values.map(value => 
        ((value / 255) * (MAX_BAR_HEIGHT - MIN_BAR_HEIGHT)) + MIN_BAR_HEIGHT
      );

      const ys = heights.map(height => 100 - height);

      animate({
        targets,
        height: heights.map(h => `${h}%`),
        y: ys,
        easing: 'easeOutQuad',
        duration: 200,
        autoplay: true,
      });

      animationFrameId = requestAnimationFrame(animateBars);
    };

    animateBars();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [audioContext]);

  return (
    <svg
      ref={containerRef}
      viewBox="0 0 100 100"
      width={200}
      height={200}
      style={{ backgroundColor: '#0f172a', borderRadius: '12px' }}
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <rect
          key={i}
          ref={el => (barsRef.current[i] = el)}
          x={i * 4 + 2}
          y={100 - MIN_BAR_HEIGHT}
          width={2}
          height={MIN_BAR_HEIGHT}
          rx={1}
          ry={1}
          fill="url(#barGradient)"
        />
      ))}
      <defs>
        <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3B82F6" />
          <stop offset="100%" stopColor="#60A5FA" />
        </linearGradient>
      </defs>
    </svg>
  );
}
