import type React from "react";
import { useState } from "react";
import { t } from "../../../shared/text";
import { Lightbox } from "../../../shared/ui/components";
import { getFilePosterUrl, getFileVideoPreviewUrl, getFileThumbnailUrl } from "../../../services/api/fileDetailsApi";

export interface DetailsPreviewSectionProps {
  isImageFile: boolean;
  isVideoFile: boolean;
  isExeSoftwareFile: boolean;
  isPdfBookFile: boolean;
  isVideoPreviewActive: boolean;
  previewLoadFailed: boolean;
  previewImageSrc: string | undefined;
  name: string;
  itemId?: number;
  metadata?: { page_count?: number | null } | null;
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
  itemId,
  metadata,
  previewRef,
  onImageError,
  onImageLoad,
}: DetailsPreviewSectionProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [pdfPage, setPdfPage] = useState(0);

  if (isVideoFile && itemId !== undefined) {
    return (
      <section className="details-preview-section">
        <div className="details-preview-section__header">
          <h4>{t("details.sections.preview")}</h4>
        </div>
        <div className="details-video-preview">
          <video controls style={{ maxWidth: "100%", maxHeight: "60vh" }} poster={getFilePosterUrl(itemId) || undefined}>
            <source src={getFileVideoPreviewUrl(itemId)} />
          </video>
        </div>
      </section>
    );
  }

  if (isPdfBookFile && itemId !== undefined) {
    const pdfPageCount = metadata?.page_count ?? 1;
    return (
      <section className="details-preview-section">
        <div className="details-preview-section__header">
          <h4>{t("details.sections.preview")}</h4>
        </div>
        <div className="pdf-preview">
          <div className="pdf-preview__toolbar">
            <button onClick={() => setPdfPage(p => Math.max(0, p - 1))} disabled={pdfPage === 0}>Prev</button>
            <span>Page {pdfPage + 1} of {pdfPageCount}</span>
            <button onClick={() => setPdfPage(p => Math.min(pdfPageCount - 1, p + 1))} disabled={pdfPage >= pdfPageCount - 1}>Next</button>
          </div>
          <img src={`${getFileThumbnailUrl(itemId)}?page=${pdfPage}`} alt={`Page ${pdfPage + 1}`} />
        </div>
      </section>
    );
  }

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
