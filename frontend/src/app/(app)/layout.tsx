'use client';

import { Sidebar } from "@/components/layout/Sidebar";
import { AddApplicationModal } from "@/components/applications";
import { AuthGuard } from "@/components/auth";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <main style={{ 
          flex: 1, 
          marginLeft: 'var(--sidebar-width)',
          transition: 'margin-left var(--transition-slow)'
        }}>
          {children}
        </main>
      </div>
      <AddApplicationModal />
    </AuthGuard>
  );
}
