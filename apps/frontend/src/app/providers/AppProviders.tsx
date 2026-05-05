import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type PropsWithChildren } from "react";
import { BrowserRouter, HashRouter } from "react-router-dom";
import { ThemeProvider } from "../../shared/theme";
import { LocaleProvider } from "../../shared/text";


export function AppProviders({ children }: PropsWithChildren) {
  const Router = window.location.protocol === "file:" ? HashRouter : BrowserRouter;
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LocaleProvider>
          <Router>{children}</Router>
        </LocaleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
