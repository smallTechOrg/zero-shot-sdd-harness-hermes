import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Music Tutor",
  description: "Learn to read staff notation — note naming drill.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
