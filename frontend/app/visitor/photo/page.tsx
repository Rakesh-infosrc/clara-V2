import React from 'react';
import VideoCapture from '@/components/VideoCapture';

export const metadata = {
  title: 'Visitor Photo Capture',
};

export default function VisitorPhotoPage() {
  return (
    <main className="min-h-screen p-6">
      <VideoCapture />
    </main>
  );
}
