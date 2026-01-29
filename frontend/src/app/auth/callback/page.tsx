'use client';

import { Suspense } from 'react';
import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import styles from './callback.module.css';

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    
    if (!accessToken) {
      console.error('No access token in callback');
      router.push('/login?error=no_token');
      return;
    }

    // Fetch user info with the token
    const fetchUser = async () => {
      try {
        const response = await fetch('http://localhost:8000/auth/me', {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch user');
        }

        const user = await response.json();
        
        // Save auth state
        setAuth(user, accessToken);
        
        // Redirect to dashboard
        router.push('/');
      } catch (error) {
        console.error('Auth callback error:', error);
        router.push('/login?error=auth_failed');
      }
    };

    fetchUser();
  }, [searchParams, setAuth, router]);

  return (
    <div className={styles.container}>
      <div className={styles.loader}>
        <div className={styles.spinner}></div>
        <h2>Signing you in...</h2>
        <p>Please wait while we complete authentication</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className={styles.container}>
        <div className={styles.loader}>
          <div className={styles.spinner}></div>
          <h2>Loading...</h2>
        </div>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
