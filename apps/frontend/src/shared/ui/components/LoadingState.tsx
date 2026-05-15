export function LoadingState({ message }: { message?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite" aria-busy="true">
      <div className="loading-state__spinner" aria-hidden="true" />
      {message ? <p className="loading-state__message">{message}</p> : null}
    </div>
  );
}
