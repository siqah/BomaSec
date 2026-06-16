import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BomaSec — SOC-in-a-Box",
  description:
    "Multi-tenant cyber-security threat monitoring platform for Kenyan institutions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
