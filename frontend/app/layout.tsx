import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { ChatProvider } from "@/components/providers/ChatProvider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Ask Youtube | Chat with YouTube Videos",
  description:
    "Ask questions about any YouTube video using AI-powered chat. Get instant answers about video content, concepts, and more.",
  keywords: ["YouTube", "AI", "chat", "video", "learning", "education"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          <ChatProvider>
            {children}
            <Toaster position="top-center" richColors />
          </ChatProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
