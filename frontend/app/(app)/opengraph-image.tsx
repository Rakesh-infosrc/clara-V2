export const dynamic = 'force-static';

export default function Image() {
  return new Response('Open Graph image generation disabled for static export.', {
    status: 501,
  });
}
