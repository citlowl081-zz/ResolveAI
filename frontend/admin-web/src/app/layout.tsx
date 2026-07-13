import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResolveAI — Admin Dashboard",
  description: "AI-powered e-commerce after-sales management",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 antialiased">{children}</body>
    </html>
  );
}
