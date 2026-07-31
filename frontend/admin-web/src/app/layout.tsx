"use client";
import { AuthProvider } from "@/lib/auth-context";
import { AdminShell } from "@/components/admin-shell";
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head><link rel="icon" href="/images/brand/logo.svg" type="image/svg+xml" /></head>
      <body className="min-h-screen antialiased">
        <AuthProvider>
          <AdminShell>{children}</AdminShell>
        </AuthProvider>
      </body>
    </html>
  );
}
