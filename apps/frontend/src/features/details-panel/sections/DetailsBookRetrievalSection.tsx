import { useNavigate } from "react-router-dom";

export interface DetailsBookRetrievalSectionProps {
  fileId: number;
  firstTag: { id: number } | null;
  colorTag: string | null;
  retrievalHintKind: string | null;
  retrievalHintMessage: string | null;
}

export function DetailsBookRetrievalSection({
  fileId,
  firstTag,
  colorTag,
  retrievalHintKind,
  retrievalHintMessage,
}: DetailsBookRetrievalSectionProps) {
  const navigate = useNavigate();
  return (
    <section className="details-retrieval-section">
      <div className="details-retrieval-section__header">
        <h4>Re-find this book</h4>
      </div>
      <p>
        {retrievalHintKind === "color"
          ? retrievalHintMessage
          : retrievalHintKind === "tag"
            ? "Tags updated. Use Tags or Books to land back on this ebook naturally."
            : "Use the shared retrieval surfaces to come back to this ebook after organizing it."}
      </p>
      <div className="details-retrieval-actions">
        {firstTag ? (
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              const params = new URLSearchParams({
                tag_id: String(firstTag.id),
                focus: String(fileId),
              });
              navigate(`/tags?${params.toString()}`);
            }}
          >
            Find in Tags
          </button>
        ) : null}
        {firstTag ? (
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              const params = new URLSearchParams({
                tag_id: String(firstTag.id),
                focus: String(fileId),
                entry: "details",
              });
              navigate(`/library/books?${params.toString()}`);
            }}
          >
            Open matching books
          </button>
        ) : null}
        {colorTag ? (
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              const params = new URLSearchParams({
                color_tag: colorTag,
                focus: String(fileId),
                entry: "details",
              });
              navigate(`/library/books?${params.toString()}`);
            }}
          >
            Filter in Books
          </button>
        ) : null}
      </div>
    </section>
  );
}
