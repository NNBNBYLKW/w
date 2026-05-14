import { useNavigate } from "react-router-dom";

export interface DetailsSoftwareRetrievalSectionProps {
  fileId: number;
  firstTag: { id: number } | null;
  colorTag: string | null;
  retrievalHintKind: string | null;
  retrievalHintMessage: string | null;
}

export function DetailsSoftwareRetrievalSection({
  fileId,
  firstTag,
  colorTag,
  retrievalHintKind,
  retrievalHintMessage,
}: DetailsSoftwareRetrievalSectionProps) {
  const navigate = useNavigate();
  return (
    <section className="details-retrieval-section">
      <div className="details-retrieval-section__header">
        <h4>Re-find this software</h4>
      </div>
      <p>
        {retrievalHintKind === "color"
          ? retrievalHintMessage
          : retrievalHintKind === "tag"
            ? "Tags updated. Use Tags or Software to land back on this software-related file naturally."
            : "Use the shared retrieval surfaces to come back to this software-related file after organizing it."}
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
              navigate(`/software?${params.toString()}`);
            }}
          >
            Open matching software
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
              navigate(`/software?${params.toString()}`);
            }}
          >
            Filter in Software
          </button>
        ) : null}
      </div>
    </section>
  );
}
