import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          padding: '40px 20px', 
          textAlign: 'center', 
          fontFamily: 'var(--font-ui)',
          color: 'var(--text-secondary)'
        }}>
          <h2 style={{ marginBottom: '12px', color: 'var(--color-warn)' }}>Something went wrong</h2>
          <p style={{ marginBottom: '16px' }}>Please refresh the app to try again.</p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              padding: '12px 24px',
              background: 'var(--accent-primary)',
              color: 'var(--text-inverted)',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            Refresh
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
