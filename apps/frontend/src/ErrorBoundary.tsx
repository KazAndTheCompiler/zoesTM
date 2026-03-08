import React, { ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

/**
 * Error Boundary component to catch and display errors in the application.
 * Prevents entire app from crashing if a component fails.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: undefined };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[Error Boundary]', error, info);
    // Could log to error reporting service here
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '2rem',
            backgroundColor: '#fee',
            border: '2px solid #f00',
            borderRadius: '8px',
            margin: '1rem',
            fontFamily: 'monospace',
          }}
          role="alert"
          aria-label="Application error"
        >
          <h2 style={{ color: '#c00', margin: '0 0 1rem 0' }}>Application Error</h2>
          <p style={{ margin: '0 0 1rem 0', color: '#333' }}>
            An unexpected error occurred. Please refresh the page or contact support.
          </p>
          <details style={{ whiteSpace: 'pre-wrap', color: '#666', fontSize: '0.85em' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>Error Details</summary>
            <code>{this.state.error?.toString()}</code>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#c00',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
