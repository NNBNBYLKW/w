import { useNavigate } from "react-router-dom";

export interface DetailsGameRetrievalSectionProps {
  fileId: number;
  firstTag: { id: number } | null;
  colorTag: string | null;
  status: string | null;
  retrievalHintKind: string | null;
  retrievalHintMessage: string | null;
}

export function DetailsGameRetrievalSection({
  fileId,
  firstTag,
  colorTag,
  status,
  retrievalHintKind,
  retrievalHintMessage,
}: DetailsGameRetrievalSectionProps) {
  const navigate = useNavigate();
  return (
    <section className="details-retrieval-section">
      <div className="details-retrieval-section__header">
        <h4>Re-find this game</h4>
      </div>
      <p>
        {retrievalHintKind === "status"
          ? retrievalHintMessage
          : retrievalHintKind === "color"
            ? retrievalHintMessage
            : retrievalHintKind === "tag"
              ? "Tags updated. Use Tags or Games to land back on this game entry naturally."
          : "Use the Games subset to come back to this game entry after opening or lightly organizing it."}
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
              if (status) {
                params.set("status", status);
              }
              navigate(`/library/games?${params.toString()}`);
            }}
          >
            Open matching games
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
              if (status) {
                params.set("status", status);
              }
              navigate(`/library/games?${params.toString()}`);
            }}
          >
            Filter in Games
          </button>
        ) : null}
        <button
          className="ghost-button"
          type="button"
          onClick={() => {
            const params = new URLSearchParams({
              focus: String(fileId),
              entry: "details",
            });
            if (status) {
              params.set("status", status);
            }
            navigate(`/library/games?${params.toString()}`);
          }}
        >
          Back to Games
        </button>
      </div>
    </section>
  );
}
