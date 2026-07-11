import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rock, Paper, Scissors — Tournament",
  description: "RPS Frontier Arena",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="cs">
      <body>{children}</body>
    </html>
  );
}
