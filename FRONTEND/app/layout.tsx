import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Flame } from "lucide-react"
import { ThemeProvider } from "@/components/theme-provider"
import { ThemeToggle } from "@/components/theme-toggle"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "MyBlazey - Agentic Orchestrator",
  description: "AI-Powered Microservice Orchestrator and Assistant",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background text-foreground antialiased selection:bg-foreground selection:text-background flex flex-col font-sans`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-md">
            <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
              <div className="flex items-center gap-2.5">
                <div className="flex size-8 items-center justify-center rounded-lg bg-foreground text-background">
                  <Flame className="size-5 fill-current" />
                </div>
                <div className="flex flex-col">
                  <span className="text-base font-semibold tracking-tight leading-none">
                    MyBlazey
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider leading-none mt-1">
                    Agentic Orchestrator
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="flex-1 flex flex-col min-h-0">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  )
}
