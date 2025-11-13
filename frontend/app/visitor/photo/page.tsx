import React from 'react';
import VisitorPhotoClient from '@/components/visitor/VisitorPhotoClient';

export const metadata = {
  title: 'Visitor Photo Capture',
};

export default function VisitorPhotoPage() {
  return (
    <main className="min-h-screen p-6">
      <VisitorPhotoClient />
    </main>
  );
}
