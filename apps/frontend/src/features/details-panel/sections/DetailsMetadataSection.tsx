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
    codec: string | null;
    bitrate: number | null;
    stream_count: number | null;
    author: string | null;
    title: string | null;
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
          {isVideoFile && metadata?.codec ? (
            <div className="details-list__row">
              <dt>{t("details.fields.codec")}</dt>
              <dd>{metadata.codec}</dd>
            </div>
          ) : null}
          {isVideoFile && metadata?.bitrate ? (
            <div className="details-list__row">
              <dt>{t("details.fields.bitrate")}</dt>
              <dd>{(metadata.bitrate / 1000).toFixed(0)} kbps</dd>
            </div>
          ) : null}
          {isVideoFile && metadata?.stream_count ? (
            <div className="details-list__row">
              <dt>{t("details.fields.streamCount")}</dt>
              <dd>{metadata.stream_count}</dd>
            </div>
          ) : null}
        </dl>
      ) : metadata === null ? (
        <p>{t("details.notes.noMetadata")}</p>
      ) : (
        <dl className="details-list">
          {metadata?.author ? (
            <div className="details-list__row">
              <dt>{t("details.fields.author")}</dt>
              <dd>{metadata.author}</dd>
            </div>
          ) : null}
          {metadata?.title ? (
            <div className="details-list__row">
              <dt>{t("details.fields.documentTitle")}</dt>
              <dd>{metadata.title}</dd>
            </div>
          ) : null}
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
