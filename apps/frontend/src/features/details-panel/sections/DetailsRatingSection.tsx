import type { FileRatingValue } from "../../../entities/file/types";
import { t } from "../../../shared/text";

export interface DetailsRatingSectionProps {
  isFavorite: boolean;
  rating: FileRatingValue | null;
  isPending: boolean;
  error: string | null;
  favoriteLabel: string;
  ratingLabel: string;
  onToggleFavorite: () => void;
  onSetRating: (value: FileRatingValue) => void;
  onClearRating: () => void;
}

export function DetailsRatingSection({
  isFavorite,
  rating,
  isPending,
  error,
  favoriteLabel,
  ratingLabel,
  onToggleFavorite,
  onSetRating,
  onClearRating,
}: DetailsRatingSectionProps) {
  return (
    <section className="details-user-meta-section">
      <div className="details-user-meta-section__header">
        <h4>{t("details.sections.favoriteAndRating")}</h4>
        {isPending ? <span className="status-pill">{t("details.actions.updating")}</span> : null}
      </div>
      <dl className="details-list">
        <div className="details-list__row">
          <dt>{t("details.fields.favorite")}</dt>
          <dd>{favoriteLabel}</dd>
        </div>
        <div className="details-list__row">
          <dt>{t("details.fields.rating")}</dt>
          <dd>{ratingLabel}</dd>
        </div>
      </dl>
      <div className="details-user-meta-actions">
        <button
          className={`ghost-button details-user-meta-button${isFavorite ? " details-user-meta-button--selected" : ""}`}
          type="button"
          onClick={onToggleFavorite}
          disabled={isPending}
        >
          {isFavorite ? t("details.actions.removeFavorite") : t("details.actions.markFavorite")}
        </button>
      </div>
      <div className="details-user-meta-rating-actions">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            className={`ghost-button details-user-meta-button${rating === value ? " details-user-meta-button--selected" : ""}`}
            type="button"
            onClick={() => onSetRating(value as FileRatingValue)}
            disabled={isPending}
          >
            ★ {value}
          </button>
        ))}
        <button
          className={`ghost-button details-user-meta-button${rating === null ? " details-user-meta-button--selected" : ""}`}
          type="button"
          onClick={onClearRating}
          disabled={isPending}
        >
          {t("details.actions.clearRating")}
        </button>
      </div>
      {error ? <p className="color-tag-section__error">{error}</p> : null}
    </section>
  );
}
