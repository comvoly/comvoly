import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Comvoly — Community intelligence",
  description: "Ask questions and discover knowledge from your authorised community archive.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
