'use client';

import { useEffect, useRef } from 'react';
import { Color, Group, MathUtils, Mesh, MeshPhysicalMaterial } from 'three';
import { Canvas, useFrame } from '@react-three/fiber';

type EmotionKey = 'neutral' | 'happy' | 'angry' | 'sleep' | 'thinking' | 'listening' | 'surprised';

function targetsForEmotion(emotion: EmotionKey) {
  switch (emotion) {
    case 'happy':
      return { pupil: 0.5, eyelid: 1, glow: 1.2, color: '#63ffda', tilt: 0 };
    case 'angry':
      return { pupil: 0.2, eyelid: 0.85, glow: 1.4, color: '#ff3b3b', tilt: -0.05 };
    case 'sleep':
      return { pupil: 0.25, eyelid: 0.1, glow: 0.4, color: '#3a4b5a', tilt: 0 };
    case 'thinking':
      return { pupil: 0.35, eyelid: 1, glow: 1.0, color: '#8b5cf6', tilt: 0 };
    case 'listening':
      return { pupil: 0.35, eyelid: 1, glow: 1.0, color: '#22d3ee', tilt: 0.03 };
    case 'surprised':
      return { pupil: 0.9, eyelid: 1, glow: 1.1, color: '#a8ffff', tilt: 0 };
    default:
      return { pupil: 0.35, eyelid: 1, glow: 0.9, color: '#00c2ff', tilt: 0 };
  }
}

function Eye({ emotion }: { emotion: EmotionKey }) {
  const group = useRef<Group>(null);
  const iris = useRef<Mesh>(null);
  const pupil = useRef<Mesh>(null);
  const topLid = useRef<Mesh>(null);
  const bottomLid = useRef<Mesh>(null);
  const eyeWhite = useRef<Mesh>(null);

  const current = useRef({
    pupil: 0.35,
    eyelid: 1,
    glow: 0.9,
    tilt: 0,
  });
  const target = useRef(targetsForEmotion('neutral'));
  // Blink timing refs (per component instance)
  const blinkNextRef = useRef<{ t: number }>({ t: 0 });
  const blinkStartRef = useRef<{ t: number }>({ t: -999 });

  useEffect(() => {
    target.current = targetsForEmotion(emotion);
  }, [emotion]);

  useFrame((state, delta) => {
    const t = target.current;
    const c = current.current;
    const baseSpd = emotion === 'sleep' ? 2 : 6;
    const spd = baseSpd * delta;

    c.pupil = MathUtils.lerp(c.pupil, t.pupil, spd);
    c.eyelid = MathUtils.lerp(c.eyelid, t.eyelid, spd);
    c.glow = MathUtils.lerp(c.glow, t.glow, spd);
    c.tilt = MathUtils.lerp(c.tilt, t.tilt, spd);

    const time = state.clock.getElapsedTime();
    let wobble = 0;
    if (emotion === 'listening') wobble = Math.sin(time * 2) * 0.04;
    const thinkPulse = emotion === 'thinking' ? 0.2 * Math.sin(time * 1.2) : 0;

    if (group.current) group.current.rotation.z = c.tilt + wobble;

    // animate iris color and glow using meshPhysicalMaterial for realism
    if (iris.current) {
      const mat = (
        Array.isArray(iris.current.material) ? iris.current.material[0] : iris.current.material
      ) as MeshPhysicalMaterial | undefined;
      if (mat) {
        const col = new Color(target.current.color);
        mat.color = col;
        mat.emissive = col.clone();
        mat.emissiveIntensity = Math.max(0, c.glow + thinkPulse);
        mat.clearcoat = 1;
        mat.clearcoatRoughness = 0.2;
        mat.roughness = 0.2;
        mat.metalness = 0.3;
        mat.needsUpdate = true;
      }
    }

    // eye whites have subtle emission for a soft glow
    if (eyeWhite.current) {
      const mat = (
        Array.isArray(eyeWhite.current.material)
          ? eyeWhite.current.material[0]
          : eyeWhite.current.material
      ) as MeshPhysicalMaterial | undefined;
      if (mat) {
        mat.emissiveIntensity = 0.4 + (emotion === 'happy' ? 0.2 : 0);
      }
    }

    // micro pupil breathing and jitter for realism
    if (pupil.current) {
      const base = 0.22;
      let s = Math.max(0.05, base * c.pupil);
      // subtle breathing and jitter
      s *= 1 + 0.05 * Math.sin(time * 6);
      const jitter = (Math.random() - 0.5) * 0.006;
      pupil.current.scale.set(s / base, s / base, 1);
      pupil.current.position.x = jitter;
      pupil.current.position.y = jitter;
    }

    // Blinking
    const BLINK_DUR = 0.18;
    if (emotion !== 'sleep' && time > blinkNextRef.current.t) {
      blinkStartRef.current.t = time;
      blinkNextRef.current.t = time + 3 + Math.random() * 3;
    }
    let blinkAmt = 0;
    const dt = time - blinkStartRef.current.t;
    if (dt >= 0 && dt <= BLINK_DUR) {
      // soften blink motion
      blinkAmt = 0.5 - 0.5 * Math.cos((dt / BLINK_DUR) * Math.PI);
    }

    if (topLid.current && bottomLid.current) {
      const open = MathUtils.clamp(c.eyelid, 0, 1);
      const blinkClose = 0.85 * blinkAmt;
      const effOpen = MathUtils.clamp(open * (1 - blinkClose), 0, 1);

      // eyelid soft curve movement
      const topY = 1.25 - effOpen * 1.21;
      const botY = -1.25 + effOpen * 1.21;
      topLid.current.position.y = topY;
      bottomLid.current.position.y = botY;
    }
  });

  return (
    <group ref={group}>
      {/* Eye White */}
      <mesh ref={eyeWhite} position={[0, 0, 0]}>
        <circleGeometry args={[1, 64]} />
        <meshPhysicalMaterial
          color="#0b0f14"
          emissive="#0b0f14"
          emissiveIntensity={0.4}
          roughness={0.6}
          metalness={0.1}
        />
      </mesh>

      {/* Iris */}
      <mesh ref={iris} position={[0, 0, 0.02]}>
        <circleGeometry args={[0.46, 64]} />
        <meshPhysicalMaterial
          color="#00c2ff"
          emissive="#00c2ff"
          emissiveIntensity={0.9}
          roughness={0.2}
          metalness={0.3}
          clearcoat={1}
          clearcoatRoughness={0.2}
        />
      </mesh>

      {/* Pupil */}
      <mesh ref={pupil} position={[0, 0, 0.04]}>
        <circleGeometry args={[0.22, 64]} />
        <meshBasicMaterial color="#000000" />
      </mesh>

      {/* Specular highlight */}
      <mesh position={[-0.18, 0.22, 0.06]}>
        <circleGeometry args={[0.06, 32]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>

      {/* Top eyelid */}
      <mesh ref={topLid} position={[0, 1.25, 0.08]} rotation={[0, 0, 0]}>
        <planeGeometry args={[2.2, 1.3]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.85} />
      </mesh>
      {/* Bottom eyelid */}
      <mesh ref={bottomLid} position={[0, -1.25, 0.08]} rotation={[0, 0, Math.PI]}>
        <planeGeometry args={[2.2, 1.3]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

function Face({ emotion, eyes = 2 }: { emotion: EmotionKey; eyes?: number }) {
  const spacing = 1.6;
  const positions = eyes >= 2 ? [-spacing / 2, spacing / 2] : [0];

  return (
    <group>
      {/* Device frame bars */}
      <mesh position={[0, 1.55, -0.02]} rotation={[0, 0, -0.05]}>
        <planeGeometry args={[4.6, 0.14]} />
        <meshStandardMaterial color="#0f141a" roughness={0.8} metalness={0.1} />
      </mesh>
      <mesh position={[0, -1.55, -0.02]} rotation={[0, 0, 0.05]}>
        <planeGeometry args={[4.6, 0.14]} />
        <meshStandardMaterial color="#0f141a" roughness={0.8} metalness={0.1} />
      </mesh>

      {positions.map((x, i) => (
        <group key={i} position={[x, 0, 0]} scale={[0.9, 0.9, 0.9]}>
          <Eye emotion={emotion} />
        </group>
      ))}
    </group>
  );
}

export default function EyeScene({
  emotion = 'neutral' as EmotionKey,
  eyes = 2,
}: {
  emotion?: EmotionKey;
  eyes?: number;
}) {
  return (
    <Canvas camera={{ position: [0, 0, 2.4], fov: 35 }} dpr={[1, 2]}>
      <color attach="background" args={['#000000']} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[2, 3, 4]} intensity={0.8} />
      <Face emotion={emotion as EmotionKey} eyes={eyes} />
    </Canvas>
  );
}
