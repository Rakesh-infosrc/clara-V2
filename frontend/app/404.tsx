import React from 'react';
import Link from 'next/link';
import AnimatedBackground from '@/components/animated-background';
import EyeScene from '@/components/robot/RobotEye3D';
import { Button } from '@/components/ui/button';

export const dynamic = 'force-static';

export default function NotFound() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-6">
      <AnimatedBackground />
      <div className="relative z-10 flex flex-col items-center gap-6 text-center">
        <div className="relative h-[160px] w-[320px] sm:h-[240px] sm:w-[520px]">
          <EyeScene emotion="surprised" eyes={2} energy={0.15} dim={1} />
        </div>
        <h1 className="bg-gradient-to-r from-cyan-300 via-sky-400 to-blue-500 bg-clip-text text-6xl font-black tracking-tight text-transparent sm:text-7xl">
          404
        </h1>
        <p className="text-muted-foreground max-w-prose">
          Clara couldn&apos;t find that page. Let&apos;s head back and start a conversation.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button asChild variant="primary" size="lg">
            <Link href="/">Go Home</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/">Talk to Clara</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
