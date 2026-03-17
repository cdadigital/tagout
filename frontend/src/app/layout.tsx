import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Tagout — Idaho Hunting Predictions",
  description:
    "2025 season predictions for Idaho Panhandle elk and deer — powered by 22 years of IDFG data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#0c0f14] text-white min-h-screen`}
      >
        <header className="border-b border-gray-800/50 bg-[#0c0f14]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-lg mx-auto px-4 h-12 flex items-center justify-between">
            <span className="text-lg font-bold text-amber-500 tracking-tight">
              TAGOUT
            </span>
            <span className="text-[10px] text-gray-600 uppercase tracking-widest">
              2025 Season
            </span>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
