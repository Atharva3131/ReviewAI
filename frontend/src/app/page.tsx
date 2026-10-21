'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// DEMO MODE: root redirects straight to dashboard — no login required
export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);
  return null;
}
