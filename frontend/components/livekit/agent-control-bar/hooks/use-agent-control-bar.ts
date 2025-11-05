import * as React from 'react';
import { Track } from 'livekit-client';
import {
  type TrackReferenceOrPlaceholder,
  useLocalParticipant,
  usePersistentUserChoices,
  useRoomContext,
  useTrackToggle,
} from '@livekit/components-react';
import { usePublishPermissions } from './use-publish-permissions';

export interface ControlBarControls {
  microphone?: boolean;
  screenShare?: boolean;
  chat?: boolean;
  camera?: boolean;
  leave?: boolean;
}

export interface UseAgentControlBarProps {
  controls?: ControlBarControls;
  saveUserChoices?: boolean;
  onDeviceError?: (error: { source: Track.Source; error: Error }) => void;
}

export interface UseAgentControlBarReturn {
  micTrackRef: TrackReferenceOrPlaceholder;
  visibleControls: ControlBarControls;
  microphoneToggle: ReturnType<typeof useTrackToggle<Track.Source.Microphone>>;
  cameraToggle: ReturnType<typeof useTrackToggle<Track.Source.Camera>>;
  screenShareToggle: ReturnType<typeof useTrackToggle<Track.Source.ScreenShare>>;
  handleDisconnect: () => void;
  handleAudioDeviceChange: (deviceId: string) => void;
  handleVideoDeviceChange: (deviceId: string) => void;
}

export function useAgentControlBar(props: UseAgentControlBarProps = {}): UseAgentControlBarReturn {
  const { controls, saveUserChoices = true } = props;
  const visibleControls = {
    leave: true,
    ...controls,
  };
  const { microphoneTrack, localParticipant } = useLocalParticipant();
  const publishPermissions = usePublishPermissions();
  const room = useRoomContext();

  const microphoneToggle = useTrackToggle({
    source: Track.Source.Microphone,
    onDeviceError: (error) => props.onDeviceError?.({ source: Track.Source.Microphone, error }),
  });
  const cameraToggle = useTrackToggle({
    source: Track.Source.Camera,
    onDeviceError: (error) => props.onDeviceError?.({ source: Track.Source.Camera, error }),
  });
  const screenShareToggle = useTrackToggle({
    source: Track.Source.ScreenShare,
    onDeviceError: (error) => props.onDeviceError?.({ source: Track.Source.ScreenShare, error }),
  });

  const { enabled: microphoneEnabled, toggle: toggleMicrophoneNative } = microphoneToggle;
  const { enabled: cameraEnabled, toggle: toggleCameraNative } = cameraToggle;
  const { enabled: screenShareEnabled, toggle: toggleScreenShareNative } = screenShareToggle;

  const micTrackRef = React.useMemo(() => {
    return {
      participant: localParticipant,
      source: Track.Source.Microphone,
      publication: microphoneTrack,
    };
  }, [localParticipant, microphoneTrack]);

  visibleControls.microphone ??= publishPermissions.microphone;
  visibleControls.screenShare ??= publishPermissions.screenShare;
  visibleControls.camera ??= publishPermissions.camera;
  visibleControls.chat ??= publishPermissions.data;

  const {
    saveAudioInputEnabled,
    saveAudioInputDeviceId,
    saveVideoInputEnabled,
    saveVideoInputDeviceId,
  } = usePersistentUserChoices({
    preventSave: !saveUserChoices,
  });

  const handleDisconnect = React.useCallback(async () => {
    if (room) {
      await room.disconnect();
    }
  }, [room]);

  const handleAudioDeviceChange = React.useCallback(
    (deviceId: string) => {
      saveAudioInputDeviceId(deviceId ?? 'default');
    },
    [saveAudioInputDeviceId]
  );

  const handleVideoDeviceChange = React.useCallback(
    (deviceId: string) => {
      saveVideoInputDeviceId(deviceId ?? 'default');
    },
    [saveVideoInputDeviceId]
  );

  const handleToggleCamera = React.useCallback(
    async (enabled?: boolean) => {
      if (screenShareEnabled) {
        await toggleScreenShareNative(false);
      }
      await toggleCameraNative(enabled);
      saveVideoInputEnabled(!cameraEnabled);
    },
    [
      cameraEnabled,
      saveVideoInputEnabled,
      screenShareEnabled,
      toggleCameraNative,
      toggleScreenShareNative,
    ]
  );

  const handleToggleMicrophone = React.useCallback(
    async (enabled?: boolean) => {
      await toggleMicrophoneNative(enabled);
      saveAudioInputEnabled(!microphoneEnabled);
    },
    [microphoneEnabled, saveAudioInputEnabled, toggleMicrophoneNative]
  );

  const handleToggleScreenShare = React.useCallback(
    async (enabled?: boolean) => {
      if (cameraEnabled) {
        await toggleCameraNative(false);
      }
      await toggleScreenShareNative(enabled);
    },
    [cameraEnabled, toggleCameraNative, toggleScreenShareNative]
  );

  return {
    micTrackRef,
    visibleControls,
    cameraToggle: {
      ...cameraToggle,
      toggle: handleToggleCamera,
    },
    microphoneToggle: {
      ...microphoneToggle,
      toggle: handleToggleMicrophone,
    },
    screenShareToggle: {
      ...screenShareToggle,
      toggle: handleToggleScreenShare,
    },
    handleDisconnect,
    handleAudioDeviceChange,
    handleVideoDeviceChange,
  };
}
