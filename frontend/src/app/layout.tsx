import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { AddApplicationModal } from "@/components/applications";
import { Providers } from "@/components/providers";

import { AuthGuard } from "@/components/auth";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Orbit — Track Your Career Journey",
  description: "The ultimate job application command center for students. Track applications, crush interviews, get hired.",
  keywords: ["job tracker", "application tracker", "career", "internship", "student jobs"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable}`}>
        <Providers>
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
        </Providers>
      </body>
    </html>
  );
}
