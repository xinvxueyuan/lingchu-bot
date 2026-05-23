import { getRSS } from '@/lib/rss';

export const revalidate = false;

export function GET() {
  return new Response(getRSS('en'), {
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}
