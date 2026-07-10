import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Auto-Podcaster",
  description: "Type a topic, pick your hosts, hear a real-time AI podcast.",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0f1115", color: "#e8e8e8" }}>
        {children}
      </body>
    </html>
  );
}
