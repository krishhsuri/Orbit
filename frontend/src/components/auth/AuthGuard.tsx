'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores';

interface AuthGuardProps {
  children: React.ReactNode;
}

// Routes that don't require authentication
const publicRoutes = ['/login', '/auth/callback'];

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, initialize } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    setMounted(true);
    // Initialize auth store (set token in API client)
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!mounted) return;

    const isPublicRoute = publicRoutes.some(route => 
      pathname === route || pathname.startsWith(route + '/')
    );

    if (!isAuthenticated && !isPublicRoute) {
      // Not authenticated and trying to access protected route
      router.push('/login');
    } else {
      setIsChecking(false);
    }
  }, [mounted, isAuthenticated, pathname, router]);

  // Don't render anything while checking auth on protected routes
  if (!mounted || isChecking) {
    const isPublicRoute = publicRoutes.some(route => 
      pathname === route || pathname.startsWith(route + '/')
    );
    
    if (!isPublicRoute) {
      return null; // Or a loading spinner
    }
  }

  return <>{children}</>;
}
