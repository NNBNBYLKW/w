import { t } from "../../../shared/text";

export interface DetailsTagsSectionProps {
  tags: ReadonlyArray<{ id: number; name: string }>;
  tagInput: string;
  isPending: boolean;
  error: string | null;
  onTagInputChange: (value: string) => void;
  onAddTag: (event: React.FormEvent) => void;
  onRemoveTag: (tagId: number) => void;
}

export function DetailsTagsSection({
  tags,
  tagInput,
  isPending,
  error,
  onTagInputChange,
  onAddTag,
  onRemoveTag,
}: DetailsTagsSectionProps) {
  return (
    <section className="tag-section">
      <div className="tag-section__header">
        <h4>{t("details.sections.tags")}</h4>
        {isPending ? <span className="status-pill">{t("details.actions.updating")}</span> : null}
      </div>
      <form className="tag-form" onSubmit={onAddTag}>
        <input
          className="text-input"
          value={tagInput}
          onChange={(event) => onTagInputChange(event.target.value)}
          placeholder={t("details.actions.addTagPlaceholder")}
          disabled={isPending}
        />
        <button className="secondary-button" type="submit" disabled={isPending}>
          {t("common.actions.addTag")}
        </button>
      </form>
      {error ? <p className="tag-section__error">{error}</p> : null}
      {tags.length === 0 ? (
        <p>{t("details.notes.noTags")}</p>
      ) : (
        <div className="tag-chip-list">
          {tags.map((tag) => (
            <div key={tag.id} className="tag-chip">
              <span>{tag.name}</span>
              <button
                className="ghost-button tag-chip__remove"
                type="button"
                onClick={() => onRemoveTag(tag.id)}
                disabled={isPending}
              >
                {t("details.actions.remove")}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
