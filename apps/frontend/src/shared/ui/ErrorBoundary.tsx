import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error.message, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100vh",
            padding: 32,
            fontFamily: '"Segoe UI", sans-serif',
            color: "#5a1f1f",
            background: "#fff8f8",
          }}
        >
          <div style={{ maxWidth: 480, textAlign: "center" }}>
            <h2 style={{ margin: "0 0 12px", fontSize: 22 }}>Something went wrong</h2>
            <p style={{ color: "#876a6a", lineHeight: 1.6, margin: "0 0 20px" }}>
              An unexpected error occurred. Try refreshing the page.
            </p>
            <details style={{ textAlign: "left", fontSize: 13, color: "#6b4f4f" }}>
              <summary style={{ cursor: "pointer", marginBottom: 8 }}>Error details</summary>
              <pre style={{
                padding: 12,
                borderRadius: 8,
                background: "#fff",
                border: "1px solid #f1c7c7",
                overflow: "auto",
                maxHeight: 200,
              }}>
                {this.state.error?.message ?? "Unknown error"}
              </pre>
            </details>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
