"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"

const origConsoleError = console.error
console.error = (...args: any[]) => {
  if (typeof args[0] === "string" && args[0].includes("Encountered a script tag")) {
    return
  }
  origConsoleError(...args)
}

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
