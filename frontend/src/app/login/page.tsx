'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/stores/auth-store';
import { Rocket, ArrowRight } from 'lucide-react';
import styles from './login.module.css';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  
  const error = searchParams.get('error');

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, mounted, router]);

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/login`;
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className={styles.container}>
      {/* Left Panel — Animation / Branding */}
      <div className={styles.leftPanel}>
        {/* Static pattern background */}
        <div className={styles.patternGrid} />
        
        {/* Branding content */}
        <div className={styles.brandContent}>
          <motion.div
            className={styles.brandLogo}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
           
          </motion.div>

          <motion.blockquote
            className={styles.testimonial}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
           
          </motion.blockquote>

          <motion.div
            className={styles.testimonialAuthor}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            
          </motion.div>

          {/* Animation placeholder — replace with your custom animation */}
          <div id="login-animation" className={styles.animationSlot}>
            {/* Drop your Lottie / video / canvas animation here */}
          </div>
        </div>

        {/* Bottom stats */}
        <motion.div
          className={styles.brandStats}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
         
        </motion.div>
      </div>

      {/* Right Panel — Login Form */}
      <div className={styles.rightPanel}>
        <motion.div 
          className={styles.formContainer}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          {/* Header */}
          <div className={styles.formHeader}>
            <h1>Sign in to Orbit</h1>
            <p>Track your applications, crush your interviews, get hired.</p>
          </div>

          {/* Error message */}
          {error && (
            <motion.div 
              className={styles.error}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              {error === 'no_token' && 'Authentication failed. Please try again.'}
              {error === 'auth_failed' && 'Could not verify your account. Please try again.'}
              {!['no_token', 'auth_failed'].includes(error) && 'An error occurred.'}
            </motion.div>
          )}

          {/* Google Login Button */}
          <button onClick={handleGoogleLogin} className={styles.googleButton}>
            <svg className={styles.googleIcon} viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Continue with Google
            <ArrowRight size={16} className={styles.buttonArrow} />
          </button>

          {/* Divider */}
          <div className={styles.divider}>
            <span>Secure authentication via Google</span>
          </div>

        </motion.div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className={styles.container}>
        <div className={styles.loading}>Loading...</div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
