'use client';

import { useMemo } from 'react';

interface Particle {
  left: number;
  top: number;
  delay: number;
  duration: number;
  scale: number;
}

const PARTICLE_COUNT = 96;

const pseudoRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

const buildParticles = () =>
  Array.from({ length: PARTICLE_COUNT }, (_, index) => {
    const base = index + 1;
    return {
      left: pseudoRandom(base * 3.17) * 100,
      top: pseudoRandom(base * 7.61) * 100,
      delay: pseudoRandom(base * 11.07) * -6,
      duration: 6 + pseudoRandom(base * 5.53) * 7,
      scale: 0.75 + pseudoRandom(base * 13.97) * 0.9,
    } satisfies Particle;
  });

const particles = buildParticles();

const AnimatedBackground = () => {
  const particleStyles = useMemo(() => particles, []);

  return (
    <div className="animated-background">
      <div className="animated-background__texture" />
      <div className="animated-background__vignette" />

      {particleStyles.map((particle, index) => (
        <span
          key={index}
          className="animated-background__particle"
          style={{
            left: `${particle.left.toFixed(4)}%`,
            top: `${particle.top.toFixed(4)}%`,
            animationDelay: `${particle.delay.toFixed(4)}s`,
            animationDuration: `${particle.duration.toFixed(4)}s`,
            transform: `scale(${particle.scale.toFixed(4)})`,
          }}
        />
      ))}

      <style jsx>{`
        .animated-background {
          pointer-events: none;
          position: fixed;
          inset: 0;
          z-index: 0;
          overflow: hidden;
          background: radial-gradient(circle at center, rgba(8, 19, 36, 0.4) 0%, rgba(3, 6, 12, 0.95) 65%, rgba(1, 2, 5, 1) 100%);
        }

        .animated-background__texture {
          position: absolute;
          inset: -20%;
          background: radial-gradient(circle at center, rgba(23, 102, 165, 0.35) 0%, rgba(18, 84, 122, 0.25) 28%, rgba(8, 20, 40, 0.15) 65%, rgba(2, 6, 12, 0) 100%);
          filter: blur(18px);
          opacity: 0.6;
          transform: scale(1.05);
        }

        .animated-background__vignette {
          position: absolute;
          inset: 0;
          background: radial-gradient(circle at center, rgba(6, 36, 61, 0.2) 0%, rgba(3, 9, 18, 0.92) 72%, rgba(2, 4, 8, 1) 100%);
          mix-blend-mode: screen;
          opacity: 0.75;
          backdrop-filter: blur(6px);
        }

        .animated-background__particle {
          position: absolute;
          width: 20px;
          height: 4px;
          border-radius: 999px;
          opacity: 0;
          background: linear-gradient(90deg, rgba(14, 165, 233, 0) 0%, rgba(56, 189, 248, 0.6) 40%, rgba(16, 185, 129, 0.9) 60%, rgba(59, 130, 246, 0) 100%);
          filter: blur(2px);
          animation-name: twinkle;
          animation-timing-function: ease-in-out;
          animation-iteration-count: infinite;
        }

        @keyframes twinkle {
          0%,
          100% {
            opacity: 0;
            transform: translate3d(0, 0, 0) rotate(0deg) scale(1);
          }

          35% {
            opacity: 0.8;
            transform: translate3d(-6px, -8px, 0) rotate(32deg) scale(1.2);
          }

          60% {
            opacity: 0.45;
            transform: translate3d(4px, 6px, 0) rotate(-18deg) scale(0.95);
          }
        }
      `}</style>
    </div>
  );
};

export default AnimatedBackground;
