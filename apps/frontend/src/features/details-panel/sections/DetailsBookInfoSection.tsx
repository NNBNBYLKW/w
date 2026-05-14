import { t } from "../../../shared/text";
import { buildBookDisplayTitle, formatBookFormatLabel, formatMetadataValue } from "../shared/detailsHelpers";

export interface DetailsBookInfoSectionProps {
  name: string;
  format: string;
  pageCount: number | null;
}

export function DetailsBookInfoSection({ name, format, pageCount }: DetailsBookInfoSectionProps) {
  return (
    <section className="details-book-info-section">
      <div className="details-book-info-section__header">
        <h4>{t("details.sections.bookInfo")}</h4>
      </div>
      <p className="details-book-info-section__note">{t("details.notes.bookInfo")}</p>
      <dl className="details-list">
        <div className="details-list__row">
          <dt>{t("details.fields.displayTitle")}</dt>
          <dd>{buildBookDisplayTitle(name)}</dd>
        </div>
        <div className="details-list__row">
          <dt>{t("details.fields.format")}</dt>
          <dd>{formatBookFormatLabel(format)}</dd>
        </div>
        <div className="details-list__row">
          <dt>{t("details.fields.pageCount")}</dt>
          <dd>{formatMetadataValue(pageCount)}</dd>
        </div>
      </dl>
    </section>
  );
}
