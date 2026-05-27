import type React from "react";
import { useState } from "react";
import { t } from "../../../shared/text";
import { Lightbox } from "../../../shared/ui/components";

export interface DetailsPreviewSectionProps {
  isImageFile: boolean;
  isVideoFile: boolean;
  isExeSoftwareFile: boolean;
  isPdfBookFile: boolean;
  isVideoPreviewActive: boolean;
  previewLoadFailed: boolean;
  previewImageSrc: string | undefined;
  name: string;
  previewRef: React.Ref<HTMLDivElement>;
  onImageError: () => void;
  onImageLoad: () => void;
}

export function DetailsPreviewSection({
  isImageFile,
  isVideoFile,
  isExeSoftwareFile,
  isPdfBookFile,
  isVideoPreviewActive,
  previewLoadFailed,
  previewImageSrc,
  name,
  previewRef,
  onImageError,
  onImageLoad,
}: DetailsPreviewSectionProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  return (
    <section className="details-preview-section">
      <div className="details-preview-section__header">
        <h4>{t("details.sections.preview")}</h4>
      </div>
      {!previewLoadFailed && (isVideoPreviewActive || previewImageSrc) ? (
        <div
          className={`details-preview-frame${isVideoPreviewActive ? " details-preview-frame--looping" : ""}${
            isExeSoftwareFile ? " details-preview-frame--software-icon" : ""
          }`}
          ref={previewRef}
        >
          <img
            className={`details-preview-image${isExeSoftwareFile ? " details-preview-image--software-icon" : ""}`}
            src={previewImageSrc}
            alt={t("details.previewAlt", { name })}
            width={320}
            height={180}
            onClick={() => setLightboxOpen(true)}
            style={{ cursor: "zoom-in" }}
            onError={onImageError}
            onLoad={onImageLoad}
          />
        </div>
      ) : (
        <div className="details-preview-frame details-preview-frame--empty">
          <p className="details-preview-state">
            {isImageFile
              ? t("details.notes.imagePreviewUnavailable")
              : isVideoFile
                ? t("details.notes.videoPreviewUnavailable")
                : isPdfBookFile
                  ? t("details.notes.pdfPreviewUnavailable")
                  : t("details.notes.softwareIconUnavailable")}
          </p>
        </div>
      )}
      {previewImageSrc && !isVideoPreviewActive ? (
        <Lightbox
          open={lightboxOpen}
          src={previewImageSrc}
          alt={t("details.previewAlt", { name })}
          onClose={() => setLightboxOpen(false)}
        />
      ) : null}
    </section>
  );
}
