import { useEffect, useRef, useState } from 'react';
import { Expression, expressionConfigs } from './expressions';

interface RoboFaceProps {
  expression: Expression;
  className?: string;
  energy?: number; // 0..1 voice energy to drive glow/pupil
}

export const RoboFace = ({ expression, className, energy = 0 }: RoboFaceProps) => {
  const [isBlinking, setIsBlinking] = useState(false);
  const config = expressionConfigs[expression];
  const eyeContainerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!config.blinkInterval) return;
    const blinkDuration = 150;
    const interval = setInterval(() => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), blinkDuration);
    }, config.blinkInterval);
    return () => clearInterval(interval);
  }, [config.blinkInterval]);

  useEffect(() => {}, [config.specialEffect]);
  useEffect(() => {}, [expression]);

  const renderEye = (eyeConfig: typeof config.leftEye) => {
    const irisSize = Math.min(eyeConfig.width, eyeConfig.height) * (config.irisScale || 0.85);
    const sEnergy = Math.max(0, Math.min(1, energy));
    const pupilSize = irisSize * (config.pupilScale || 0.65) * (1 - 0.12 * sEnergy);
    const blinkScale = isBlinking ? 0.05 : 1;

    return (
      <g>
        <ellipse
          cx={eyeConfig.x}
          cy={eyeConfig.y}
          rx={eyeConfig.width / 2 + 8}
          ry={(eyeConfig.height / 2) * blinkScale + 8}
          fill="none"
          stroke="hsl(var(--robo-glow))"
          strokeWidth="0.5"
          opacity="0.15"
          filter="blur(12px)"
          className={config.animation ? `animate-${config.animation}` : ''}
        />
        <ellipse
          cx={eyeConfig.x}
          cy={eyeConfig.y}
          rx={eyeConfig.width / 2 + 5}
          ry={(eyeConfig.height / 2) * blinkScale + 5}
          fill="none"
          stroke="hsl(var(--robo-eye))"
          strokeWidth="1"
          opacity="0.25"
          filter="blur(8px)"
          className={config.animation ? `animate-${config.animation}` : ''}
        />

        <ellipse
          cx={eyeConfig.x}
          cy={eyeConfig.y}
          rx={eyeConfig.width / 2}
          ry={(eyeConfig.height / 2) * blinkScale}
          fill="hsl(var(--robo-bg))"
          stroke="url(#neon-gradient)"
          strokeWidth="4"
          transform={`rotate(${eyeConfig.rotation} ${eyeConfig.x} ${eyeConfig.y})`}
          className="transition-all duration-150 ease-out"
          filter="drop-shadow(0 0 6px hsl(var(--robo-eye)))"
        />

        <ellipse
          cx={eyeConfig.x}
          cy={eyeConfig.y}
          rx={eyeConfig.width / 2 - 3}
          ry={(eyeConfig.height / 2 - 3) * blinkScale}
          fill="none"
          stroke="hsl(var(--robo-eye))"
          strokeWidth="1"
          opacity="0.4"
          transform={`rotate(${eyeConfig.rotation} ${eyeConfig.x} ${eyeConfig.y})`}
          className="transition-all duration-150 ease-out"
        />

        {!isBlinking && (
          <>
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x}
              cy={eyeConfig.y + config.pupilOffset.y}
              rx={irisSize / 2 + 4}
              ry={irisSize / 2 + 4}
              fill="hsl(var(--robo-eye))"
              opacity={0.25 + 0.55 * sEnergy}
              filter="blur(8px)"
              className={
                config.animation ? `animate-${config.animation}` : 'transition-all duration-300'
              }
            />
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x}
              cy={eyeConfig.y + config.pupilOffset.y}
              rx={irisSize / 2}
              ry={irisSize / 2}
              fill="url(#iris-gradient)"
              className={
                config.animation ? `animate-${config.animation}` : 'transition-all duration-300'
              }
            />
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x}
              cy={eyeConfig.y + config.pupilOffset.y}
              rx={irisSize / 2}
              ry={irisSize / 2}
              fill="none"
              stroke="hsl(var(--robo-glow))"
              strokeWidth="1.5"
              opacity="0.6"
              className={
                config.animation ? `animate-${config.animation}` : 'transition-all duration-300'
              }
            />
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x}
              cy={eyeConfig.y + config.pupilOffset.y}
              rx={pupilSize / 2 + 3}
              ry={pupilSize / 2 + 3}
              fill="hsl(var(--robo-bg))"
              opacity="0.4"
              filter="blur(6px)"
              className={
                config.animation ? `animate-${config.animation}` : 'transition-all duration-300'
              }
            />
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x}
              cy={eyeConfig.y + config.pupilOffset.y}
              rx={pupilSize / 2}
              ry={pupilSize / 2}
              fill="hsl(var(--robo-bg))"
              className={
                config.animation ? `animate-${config.animation}` : 'transition-all duration-300'
              }
            />

            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x - pupilSize * 0.25}
              cy={eyeConfig.y + config.pupilOffset.y - pupilSize * 0.3}
              rx={pupilSize * 0.2}
              ry={pupilSize * 0.2}
              fill="hsl(var(--robo-glow))"
              opacity="0.9"
            />
            <ellipse
              cx={eyeConfig.x + config.pupilOffset.x + pupilSize * 0.3}
              cy={eyeConfig.y + config.pupilOffset.y - pupilSize * 0.2}
              rx={pupilSize * 0.1}
              ry={pupilSize * 0.1}
              fill="hsl(var(--robo-glow))"
              opacity="0.6"
            />
          </>
        )}

        {config.eyelidTop && (
          <rect
            x={eyeConfig.x - eyeConfig.width / 2 - 5}
            y={eyeConfig.y - eyeConfig.height / 2 - 10}
            width={eyeConfig.width + 10}
            height={config.eyelidTop}
            fill="url(#eyelid-gradient)"
            className="transition-all duration-300"
          />
        )}
        {config.eyelidBottom && (
          <rect
            x={eyeConfig.x - eyeConfig.width / 2 - 5}
            y={eyeConfig.y + eyeConfig.height / 2 - config.eyelidBottom + 10}
            width={eyeConfig.width + 10}
            height={config.eyelidBottom}
            fill="url(#eyelid-gradient)"
            className="transition-all duration-300"
          />
        )}
      </g>
    );
  };

  return (
    <div className={`relative mx-auto w-full max-w-4xl ${className ?? ''}`}>
      <div className="relative aspect-[4/3] min-h-[22rem] md:min-h-[28rem]">
        <svg
          ref={eyeContainerRef}
          viewBox="0 0 240 160"
          className="relative z-0 h-full w-full origin-center translate-y-1 scale-[1]"
        >
          <defs>
            <linearGradient id="neon-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="hsl(var(--robo-glow))" stopOpacity="1" />
              <stop offset="50%" stopColor="hsl(var(--robo-eye))" stopOpacity="1" />
              <stop offset="100%" stopColor="hsl(var(--robo-glow))" stopOpacity="0.8" />
            </linearGradient>
            <radialGradient id="iris-gradient">
              <stop offset="0%" stopColor="hsl(var(--robo-glow))" stopOpacity="0.3" />
              <stop offset="40%" stopColor="hsl(var(--robo-eye))" stopOpacity="0.8" />
              <stop offset="70%" stopColor="hsl(var(--robo-eye))" stopOpacity="1" />
              <stop offset="100%" stopColor="hsl(190 100% 35%)" stopOpacity="1" />
            </radialGradient>
            <linearGradient id="eyelid-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="hsl(var(--robo-bg))" stopOpacity="1" />
              <stop offset="100%" stopColor="hsl(var(--robo-bg))" stopOpacity="0.95" />
            </linearGradient>
          </defs>

          {renderEye(config.leftEye)}
          {renderEye(config.rightEye)}
        </svg>
      </div>
    </div>
  );
};

export default RoboFace;
