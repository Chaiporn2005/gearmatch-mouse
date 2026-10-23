import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GearMatch — Find your next mouse",
  description: "Find a mouse that fits your work, play and budget, with source-grounded recommendations.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="th">
      <body className="antialiased">{children}</body>
    </html>
  );
}
