import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'

interface ErrorBoundaryState {
  error: Error | null
}

export class ErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Agartha frontend boundary', error, info)
  }

  render() {
    if (!this.state.error) {
      return this.props.children
    }

    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="max-w-md rounded-lg border bg-card p-6 text-card-foreground">
          <h1 className="text-lg font-semibold tracking-normal">
            Algo fallo en la interfaz
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            La sesion sigue intacta. Recarga la vista para reintentar.
          </p>
          <Button
            className="mt-5"
            onClick={() => this.setState({ error: null })}
            type="button"
          >
            Reintentar
          </Button>
        </div>
      </main>
    )
  }
}
