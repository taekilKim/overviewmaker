import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Overviewer for BOSS GOLF",
  description: "BOSS GOLF overview PPT generator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
