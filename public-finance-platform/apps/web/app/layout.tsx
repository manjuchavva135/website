import "./globals.css";
import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: {
    default: "AP Finance Transparency Platform",
    template: "%s | AP Finance",
  },
  description:
    "Andhra Pradesh public-finance transparency portal — debt, receipts, expenditure, deficits, and full provenance from source to row.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
