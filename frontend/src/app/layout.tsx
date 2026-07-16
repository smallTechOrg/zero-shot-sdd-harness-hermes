import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "CCTNS Analyst",
  description: "Natural-language → bounded SQL over the CCTNS mirror",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
