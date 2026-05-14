import { t } from "../../../shared/text";
import { formatDimensions, formatDurationMs, formatMetadataValue } from "../shared/detailsHelpers";

export interface DetailsMetadataSectionProps {
  isMediaFile: boolean;
  isVideoFile: boolean;
  isBookContext: boolean;
  metadata: {
    width: number | null;
    height: number | null;
    duration_ms: number | null;
    page_count: number | null;
  } | null;
}

export function DetailsMetadataSection({
  isMediaFile,
  isVideoFile,
  isBookContext,
  metadata,
}: DetailsMetadataSectionProps) {
  return (
    <section className="metadata-section">
      <div className="metadata-section__header">
        <h4>
          {isMediaFile
            ? t("details.sections.mediaInfo")
            : isBookContext
              ? t("details.sections.documentMetadata")
              : t("details.sections.metadata")}
        </h4>
      </div>
      {isMediaFile ? (
        <dl className="details-list">
          <div className="details-list__row">
            <dt>{t("details.fields.dimensions")}</dt>
            <dd>{formatDimensions(metadata?.width ?? null, metadata?.height ?? null)}</dd>
          </div>
          {isVideoFile ? (
            <div className="details-list__row">
              <dt>{t("details.fields.duration")}</dt>
              <dd>{formatDurationMs(metadata?.duration_ms)}</dd>
            </div>
          ) : null}
        </dl>
      ) : metadata === null ? (
        <p>{t("details.notes.noMetadata")}</p>
      ) : (
        <dl className="details-list">
          <div className="details-list__row">
            <dt>{t("details.fields.pageCount")}</dt>
            <dd>{formatMetadataValue(metadata.page_count)}</dd>
          </div>
          {isBookContext ? null : (
            <div className="details-list__row">
              <dt>{t("details.fields.width")}</dt>
              <dd>{formatMetadataValue(metadata.width, "px")}</dd>
            </div>
          )}
          {isBookContext ? null : (
            <div className="details-list__row">
              <dt>{t("details.fields.height")}</dt>
              <dd>{formatMetadataValue(metadata.height, "px")}</dd>
            </div>
          )}
          <div className="details-list__row">
            <dt>{t("details.fields.duration")}</dt>
            <dd>{formatDurationMs(metadata.duration_ms)}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
