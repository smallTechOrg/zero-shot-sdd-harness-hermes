import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "MSSQL Analyst",
  description: "Natural-language analyst over a live Microsoft SQL Server database",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
