export type Expression =
  | 'neutral'
  | 'happy'
  | 'angry'
  | 'sleep'
  | 'thinking'
  | 'listening'
  | 'surprised'
  | 'sad'
  | 'excited'
  | 'confused'
  | 'loving'
  | 'processing'
  | 'error'
  | 'success';

export interface EyeConfig {
  leftEye: {
    width: number;
    height: number;
    x: number;
    y: number;
    rotation: number;
    scaleX?: number;
    scaleY?: number;
  };
  rightEye: {
    width: number;
    height: number;
    x: number;
    y: number;
    rotation: number;
    scaleX?: number;
    scaleY?: number;
  };
  pupilOffset: {
    x: number;
    y: number;
  };
  pupilScale?: number;
  eyelidTop?: number;
  eyelidBottom?: number;
  animation?: string;
  blinkInterval?: number;
  irisScale?: number;
  eyeShape?: 'circle' | 'oval' | 'almond' | 'wide';
  specialEffect?: 'stars' | 'hearts' | 'sparkles' | 'error' | 'success';
  eyeBrightness?: number;
}

export const expressionConfigs: Record<Expression, EyeConfig> = {
  neutral: {
    leftEye: { width: 50, height: 50, x: 70, y: 80, rotation: 0 },
    rightEye: { width: 50, height: 50, x: 170, y: 80, rotation: 0 },
    pupilOffset: { x: 0, y: 0 },
    pupilScale: 0.65,
    irisScale: 0.85,
    eyeShape: 'circle',
    blinkInterval: 3000,
  },
  happy: {
    leftEye: { width: 52, height: 42, x: 68, y: 85, rotation: 0, scaleY: 0.8 },
    rightEye: { width: 52, height: 42, x: 168, y: 85, rotation: 0, scaleY: 0.8 },
    pupilOffset: { x: 0, y: -3 },
    pupilScale: 0.7,
    irisScale: 0.9,
    eyelidBottom: 18,
    eyeShape: 'almond',
    blinkInterval: 2000,
  },
  angry: {
    leftEye: { width: 48, height: 38, x: 70, y: 75, rotation: 0 },
    rightEye: { width: 48, height: 38, x: 170, y: 75, rotation: 0 },
    pupilOffset: { x: 0, y: -5 },
    pupilScale: 0.5,
    irisScale: 0.75,
    eyelidTop: 22,
    eyeShape: 'almond',
    blinkInterval: 5000,
  },
  sleep: {
    leftEye: { width: 50, height: 6, x: 70, y: 90, rotation: 0 },
    rightEye: { width: 50, height: 6, x: 170, y: 90, rotation: 0 },
    pupilOffset: { x: 0, y: 0 },
    pupilScale: 0,
    eyelidTop: 45,
    eyelidBottom: 45,
    eyeShape: 'oval',
  },
  thinking: {
    leftEye: { width: 48, height: 48, x: 70, y: 80, rotation: 0 },
    rightEye: { width: 52, height: 52, x: 170, y: 78, rotation: 0 },
    pupilOffset: { x: 12, y: -8 },
    pupilScale: 0.6,
    irisScale: 0.8,
    animation: 'eye-move',
    eyeShape: 'circle',
    blinkInterval: 4000,
  },
  listening: {
    leftEye: { width: 54, height: 54, x: 68, y: 78, rotation: 0 },
    rightEye: { width: 54, height: 54, x: 168, y: 78, rotation: 0 },
    pupilOffset: { x: -8, y: 0 },
    pupilScale: 0.7,
    irisScale: 0.95,
    animation: 'glow',
    eyeShape: 'wide',
    blinkInterval: 2500,
  },
  surprised: {
    leftEye: { width: 58, height: 58, x: 68, y: 75, rotation: 0 },
    rightEye: { width: 58, height: 58, x: 168, y: 75, rotation: 0 },
    pupilOffset: { x: 0, y: -10 },
    pupilScale: 0.45,
    irisScale: 0.7,
    eyeShape: 'wide',
    blinkInterval: 8000,
  },
  sad: {
    leftEye: { width: 46, height: 50, x: 70, y: 82, rotation: 0, scaleY: 1.1 },
    rightEye: { width: 46, height: 50, x: 170, y: 82, rotation: 0, scaleY: 1.1 },
    pupilOffset: { x: 0, y: 10 },
    pupilScale: 0.75,
    irisScale: 0.9,
    eyelidTop: 12,
    eyeShape: 'oval',
    blinkInterval: 4500,
  },
  excited: {
    leftEye: { width: 56, height: 52, x: 68, y: 76, rotation: -5 },
    rightEye: { width: 56, height: 52, x: 168, y: 76, rotation: 5 },
    pupilOffset: { x: 0, y: -12 },
    pupilScale: 0.5,
    irisScale: 0.8,
    specialEffect: 'stars',
    animation: 'float',
    eyeShape: 'wide',
    eyeBrightness: 1.4,
    blinkInterval: 1200,
  },
  confused: {
    leftEye: { width: 50, height: 50, x: 70, y: 80, rotation: 0 },
    rightEye: { width: 44, height: 54, x: 170, y: 78, rotation: 0 },
    pupilOffset: { x: 6, y: 4 },
    pupilScale: 0.6,
    irisScale: 0.85,
    eyeShape: 'circle',
    blinkInterval: 3500,
  },
  loving: {
    leftEye: { width: 48, height: 52, x: 70, y: 78, rotation: -8 },
    rightEye: { width: 48, height: 52, x: 170, y: 78, rotation: 8 },
    pupilOffset: { x: 0, y: -6 },
    pupilScale: 0.8,
    irisScale: 0.95,
    specialEffect: 'hearts',
    eyeShape: 'almond',
    eyeBrightness: 1.2,
    blinkInterval: 2800,
  },
  processing: {
    leftEye: { width: 52, height: 52, x: 70, y: 80, rotation: 0 },
    rightEye: { width: 52, height: 52, x: 170, y: 80, rotation: 0 },
    pupilOffset: { x: 0, y: 0 },
    pupilScale: 0.4,
    irisScale: 0.7,
    specialEffect: 'sparkles',
    animation: 'glow',
    eyeShape: 'circle',
    blinkInterval: 4000,
  },
  error: {
    leftEye: { width: 46, height: 46, x: 70, y: 80, rotation: 0 },
    rightEye: { width: 46, height: 46, x: 170, y: 80, rotation: 0 },
    pupilOffset: { x: 0, y: 0 },
    pupilScale: 0.3,
    irisScale: 0.6,
    specialEffect: 'error',
    animation: 'glow',
    eyeShape: 'circle',
    blinkInterval: 6000,
  },
  success: {
    leftEye: { width: 54, height: 48, x: 68, y: 82, rotation: 0 },
    rightEye: { width: 54, height: 48, x: 168, y: 82, rotation: 0 },
    pupilOffset: { x: 0, y: -5 },
    pupilScale: 0.75,
    irisScale: 0.9,
    specialEffect: 'success',
    eyeShape: 'almond',
    eyeBrightness: 1.3,
    blinkInterval: 2200,
  },
};
