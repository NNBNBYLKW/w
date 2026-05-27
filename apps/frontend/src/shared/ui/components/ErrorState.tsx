export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <p className="error-state__message">{message}</p>
      {onRetry ? (
        <button className="secondary-button error-state__retry" type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
