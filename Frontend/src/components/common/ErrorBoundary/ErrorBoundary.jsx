import React from "react"
import { AlertCircle, RefreshCw } from "lucide-react"

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("[GlobalPulse ErrorBoundary Caught Exception]:", error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    if (this.props.onReset) {
      this.props.onReset()
    } else {
      window.location.reload()
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          style={{
            padding: "40px 24px",
            margin: "24px auto",
            maxWidth: "600px",
            background: "#0f172a",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "12px",
            color: "#f8fafc",
            textAlign: "center",
            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
          }}
        >
          <AlertCircle size={42} color="#ef4444" style={{ margin: "0 auto 16px", display: "block" }} />
          <h2 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "8px" }}>
            {this.props.title || "Something went wrong loading this component"}
          </h2>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px", lineHeight: "1.5" }}>
            {this.state.error?.message || "An unexpected rendering error occurred. The application remains active."}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 18px",
              background: "#2563eb",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "background 0.15s ease",
            }}
          >
            <RefreshCw size={15} />
            <span>Reload Component</span>
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
