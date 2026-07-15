import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "#local Analytics",
  description: "Full-stack acquisition + retention funnel",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
