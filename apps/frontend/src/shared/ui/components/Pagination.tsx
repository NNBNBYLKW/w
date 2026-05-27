interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showPageInput?: boolean;
}

export function Pagination({ page, totalPages, onPageChange, showPageInput = false }: PaginationProps) {
  if (totalPages <= 0) return <p className="library-muted-line">No results</p>;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "center", padding: "12px 0" }}>
      <button className="secondary-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <span style={{ fontSize: 13, color: "var(--color-text-secondary, #666)" }}>
        Page {page} of {totalPages}
      </span>
      <button className="secondary-button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
      {showPageInput && (
        <form onSubmit={(e) => { e.preventDefault(); const input = (e.target as HTMLFormElement).querySelector("input"); if (input) onPageChange(Number(input.value)); }}>
          <input type="number" min={1} max={totalPages} defaultValue={page} style={{ width: 60 }} />
        </form>
      )}
    </div>
  );
}
