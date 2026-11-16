import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "QAAI — Quality Assurance AI",
    template: "%s · QAAI",
  },
  description:
    "Conversational course evaluation with structured, privacy-first quality assurance insights.",
  applicationName: "QAAI",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
