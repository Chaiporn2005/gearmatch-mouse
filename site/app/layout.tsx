import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GearMatch — Find your next mouse",
  description: "Find a mouse that fits your work, play and budget, with source-grounded recommendations.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#12130f",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,100..900&family=Geist+Mono:wght@400..600&family=Hanken+Grotesk:wght@300..800&family=Noto+Sans+Thai:wght@300..700&display=swap"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
