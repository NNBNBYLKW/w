import { useNavigate } from "react-router-dom";

export interface DetailsMediaRetrievalSectionProps {
  fileId: number;
  firstTag: { id: number } | null;
  colorTag: string | null;
  retrievalMessage: string | null;
}

export function DetailsMediaRetrievalSection({
  fileId,
  firstTag,
  colorTag,
  retrievalMessage,
}: DetailsMediaRetrievalSectionProps) {
  const navigate = useNavigate();
  return (
    <section className="details-retrieval-section">
      <div className="details-retrieval-section__header">
        <h4>Re-find this media</h4>
      </div>
      <p>{retrievalMessage ?? "Use the shared retrieval surfaces to come back to this media after organizing it."}</p>
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
              navigate(`/library/media?${params.toString()}`);
            }}
          >
            Filter in Media
          </button>
        ) : null}
      </div>
    </section>
  );
}
