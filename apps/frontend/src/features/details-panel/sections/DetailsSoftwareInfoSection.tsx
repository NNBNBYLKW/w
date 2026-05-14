import { t } from "../../../shared/text";
import { buildSoftwareDisplayTitle, buildSoftwareEntryTypeLabel, formatSoftwareFormatLabel } from "../shared/detailsHelpers";

export interface DetailsSoftwareInfoSectionProps {
  name: string;
  format: "exe" | "msi" | "zip";
}

export function DetailsSoftwareInfoSection({ name, format }: DetailsSoftwareInfoSectionProps) {
  return (
    <section className="details-software-info-section">
      <div className="details-software-info-section__header">
        <h4>{t("details.sections.softwareInfo")}</h4>
      </div>
      <p className="details-software-info-section__note">{t("details.notes.softwareInfo")}</p>
      <dl className="details-list">
        <div className="details-list__row">
          <dt>{t("details.fields.displayTitle")}</dt>
          <dd>{buildSoftwareDisplayTitle(name)}</dd>
        </div>
        <div className="details-list__row">
          <dt>{t("details.fields.format")}</dt>
          <dd>{formatSoftwareFormatLabel(format)}</dd>
        </div>
        <div className="details-list__row">
          <dt>{t("details.fields.entryType")}</dt>
          <dd>{buildSoftwareEntryTypeLabel(format)}</dd>
        </div>
      </dl>
    </section>
  );
}
