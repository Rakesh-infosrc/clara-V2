import React, { useMemo } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import { type TrackReference, useLocalParticipant, useTracks } from '@livekit/components-react';
import AgentRoboFace from '@/components/robot/AgentRoboFace';
import { cn } from '@/lib/utils';
import { VideoTile } from './video-tile';

const MotionVideoTile = motion.create(VideoTile);
const MotionAgentRoboFace = motion.create(AgentRoboFace);

const animationProps = {
  initial: {
    opacity: 0,
    scale: 0,
  },
  animate: {
    opacity: 1,
    scale: 1,
  },
  exit: {
    opacity: 0,
    scale: 0,
  },
  transition: {
    stiffness: 675,
    damping: 75,
    mass: 1,
  },
};

const classNames = {
  // GRID
  // 2 Columns x 3 Rows
  grid: [
    'grid h-full w-full gap-x-2 place-content-center',
    'grid-cols-[1fr_1fr] grid-rows-[90px_1fr_90px]',
  ],
  // Agent
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 1 / Row 1
  // align: x-end y-center
  agentChatOpenWithSecondTile: ['col-start-1 row-start-1', 'self-center justify-self-end'],
  // Agent
  // chatOpen: true,
  // hasSecondTile: false
  // layout: Column 1 / Row 1 / Column-Span 2
  // align: x-center y-center
  agentChatOpenWithoutSecondTile: ['col-start-1 row-start-1', 'col-span-2', 'place-content-center'],
  // Agent
  // chatOpen: false
  // layout: Column 1 / Row 1 / Column-Span 2 / Row-Span 3
  // align: x-center y-center
  agentChatClosed: ['col-start-1 row-start-1', 'col-span-2 row-span-3', 'place-content-center'],
  // Second tile
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 2 / Row 1
  // align: x-start y-center
  secondTileChatOpen: ['col-start-2 row-start-1', 'self-center justify-self-start'],
  // Second tile
  // chatOpen: false,
  // hasSecondTile: false
  // layout: Column 2 / Row 2
  // align: x-end y-end
  secondTileChatClosed: ['col-start-2 row-start-3', 'place-content-end'],
};

export function useLocalTrackRef(source: Track.Source) {
  const { localParticipant } = useLocalParticipant();
  const publication = localParticipant.getTrackPublication(source);
  const trackRef = useMemo<TrackReference | undefined>(
    () => (publication ? { source, participant: localParticipant, publication } : undefined),
    [source, publication, localParticipant]
  );
  return trackRef;
}

interface MediaTilesProps {
  chatOpen: boolean;
}

export function MediaTiles({ chatOpen }: MediaTilesProps) {
  const [screenShareTrack] = useTracks([Track.Source.ScreenShare]);
  const cameraTrack: TrackReference | undefined = useLocalTrackRef(Track.Source.Camera);

  const isCameraEnabled = cameraTrack && !cameraTrack.publication.isMuted;
  const isScreenShareEnabled = screenShareTrack && !screenShareTrack.publication.isMuted;
  const hasSecondTile = isCameraEnabled || isScreenShareEnabled;

  const transition = {
    ...animationProps.transition,
    delay: chatOpen ? 0 : 0.15, // delay on close
  };
  const agentAnimate = {
    ...animationProps.animate,
    scale: chatOpen ? 1 : 3,
  };
  const agentLayoutTransition = transition;

  // We now always render eyes for the agent tile, regardless of avatar presence.

  return (
    <div className="pointer-events-none fixed inset-x-0 top-1/2 z-40 -translate-y-1/2 px-4 md:px-0">
      <div className="mx-auto w-full max-w-2xl">
        <div className="relative aspect-[4/3]">
          <div className={cn('absolute inset-0', classNames.grid)}>
            {/* agent */}
            <div
              className={cn([
                'grid',
                !chatOpen && classNames.agentChatClosed,
                chatOpen && hasSecondTile && classNames.agentChatOpenWithSecondTile,
                chatOpen && !hasSecondTile && classNames.agentChatOpenWithoutSecondTile,
              ])}
            >
              <AnimatePresence mode="popLayout">
                <MotionAgentRoboFace
                  key="agent-roboface"
                  layoutId="agent"
                  {...animationProps}
                  animate={agentAnimate}
                  transition={agentLayoutTransition}
                  className={cn(chatOpen ? 'h-[90px]' : 'h-[260px] w-full max-w-[640px]')}
                />
              </AnimatePresence>
            </div>
            <div
              className={cn([
                'grid',
                chatOpen && classNames.secondTileChatOpen,
                !chatOpen && classNames.secondTileChatClosed,
              ])}
            >
              {/* camera */}
              <AnimatePresence>
                {cameraTrack && isCameraEnabled && (
                  <MotionVideoTile
                    key="camera"
                    layout="position"
                    layoutId="camera"
                    {...animationProps}
                    trackRef={cameraTrack}
                    transition={{
                      ...animationProps.transition,
                      delay: chatOpen ? 0 : 0.15,
                    }}
                    className="h-[90px]"
                  />
                )}
                {/* screen */}
                {isScreenShareEnabled && (
                  <MotionVideoTile
                    key="screen"
                    layout="position"
                    layoutId="screen"
                    {...animationProps}
                    trackRef={screenShareTrack}
                    transition={{
                      ...animationProps.transition,
                      delay: chatOpen ? 0 : 0.15,
                    }}
                    className="h-[90px]"
                  />
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
