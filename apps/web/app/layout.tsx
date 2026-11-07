import type { Metadata } from "next";
import { vi } from "@/messages/vi";
import { themeBootstrap } from "@/lib/theme";
import "@xyflow/react/dist/style.css";
import "./globals.css";
import "./theme.css";
export const metadata: Metadata = {
  title: `${vi.app} — ${vi.tagline}`,
  description: vi.intro,
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
