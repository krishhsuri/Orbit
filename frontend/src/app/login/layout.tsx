import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login — Orbit",
  description: "Sign in to Orbit to track your job applications",
};

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Login page has its own layout without sidebar
  return <>{children}</>;
}
