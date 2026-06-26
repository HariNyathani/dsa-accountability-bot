import { Component, type ErrorInfo, type ReactNode } from "react";
import s from "./ErrorBoundary.module.css";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

/**
 * Catches render errors in the React tree so an unhandled exception in any
 * page component doesn't blank the entire app. Renders a glass-styled
 * fallback with a reload button.
 *
 * Usage: wrap <Outlet /> (or any subtree) with <ErrorBoundary>.
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message =
      error instanceof Error ? error.message : "An unexpected error occurred.";
    return { hasError: true, message };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    // In production you'd ship this to an error-tracking service (e.g. Sentry).
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, message: "" });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className={s.wrap}>
          <div className={s.card}>
            <div className={s.icon}>💥</div>
            <h2 className={s.title}>Something went wrong</h2>
            <p className={s.subtitle}>
              An unexpected error occurred in this section. You can try going
              back or reloading the page.
            </p>
            {this.state.message && (
              <pre className={s.detail}>{this.state.message}</pre>
            )}
            <div className={s.actions}>
              <button className={s.btnGhost} onClick={this.handleReset}>
                ↻ Try again
              </button>
              <button className={s.btnPrimary} onClick={this.handleReload}>
                Reload page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
