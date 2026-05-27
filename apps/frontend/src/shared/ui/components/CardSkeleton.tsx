interface CardSkeletonProps {
  count?: number;
  variant?: "card" | "row";
}

export function CardSkeleton({ count = 6, variant = "card" }: CardSkeletonProps) {
  return (
    <div className={`skeleton-grid skeleton-grid--${variant}`} aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton-pulse" style={{ height: variant === "card" ? 120 : 40, borderRadius: 8 }} />
        </div>
      ))}
    </div>
  );
}
