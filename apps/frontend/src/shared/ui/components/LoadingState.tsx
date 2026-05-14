export function LoadingState({ message }: { message?: string }) {
  return (
    <div className="loading-state">
      <div className="loading-state__spinner" />
      {message ? <p className="loading-state__message">{message}</p> : null}
    </div>
  );
}
