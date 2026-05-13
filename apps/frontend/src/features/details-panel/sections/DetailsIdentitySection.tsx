import { t } from "../../../shared/text";

export interface DetailsIdentitySectionProps {
  name: string;
  fileType: string;
  id: number;
}

export function DetailsIdentitySection({ name, fileType, id }: DetailsIdentitySectionProps) {
  return (
    <section className="details-panel__identity">
      <span className="placeholder-pill">{t("details.placeholders.indexedFile")}</span>
      <h3 className="details-panel__title" title={name}>
        {name}
      </h3>
      <div className="details-panel__identity-meta">
        <span>{fileType}</span>
        <span>#{id}</span>
      </div>
    </section>
  );
}
