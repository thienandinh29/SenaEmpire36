import type { Metadata } from "next";
import localFont from "next/font/local";
import { vi } from "@/messages/vi";
import { themeBootstrap } from "@/lib/theme";
import "@xyflow/react/dist/style.css";
import "./globals.css";
import "./theme.css";
import "./journal.css";
const journalFont = localFont({
  src: [
    { path: "./fonts/Lora-Regular.ttf", weight: "400 700", style: "normal" },
    { path: "./fonts/Lora-Italic.ttf", weight: "400 700", style: "italic" },
  ],
  variable: "--font-journal",
  preload: false,
  display: "swap",
  fallback: ["Georgia", "Times New Roman", "serif"],
  adjustFontFallback: "Times New Roman",
});
const headingFont = localFont({
  src: [
    {
      path: "./fonts/be-vietnam-pro/BeVietnamPro-SemiBold.ttf",
      weight: "600",
      style: "normal",
    },
    {
      path: "./fonts/be-vietnam-pro/BeVietnamPro-Bold.ttf",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-heading",
  preload: false,
  display: "swap",
  fallback: ["Segoe UI", "Arial", "sans-serif"],
  adjustFontFallback: "Arial",
});
const displayFont = localFont({
  src: "./fonts/dancing-script/DancingScript-Variable.ttf",
  variable: "--font-display",
  weight: "400 700",
  style: "normal",
  display: "swap",
  fallback: ["Georgia", "serif"],
  adjustFontFallback: "Times New Roman",
});
export const metadata: Metadata = {
  title: `${vi.app} — ${vi.tagline}`,
  description: vi.intro,
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="vi"
      className={`${journalFont.variable} ${headingFont.variable} ${displayFont.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
