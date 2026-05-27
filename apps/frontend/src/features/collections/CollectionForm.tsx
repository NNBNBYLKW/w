import type { ColorTagValue, FileType } from "../../entities/file/types";
import type { SourceVM } from "../../entities/source/types";
import type { TagItemVM } from "../../entities/tag/types";
import { t } from "../../shared/text";

export interface CollectionFormProps {
  isEditingSelected: boolean;
  entryNote: string | null;
  name: string;
  fileType: FileType | "";
  tagId: string;
  colorTag: ColorTagValue | "";
  sourceId: string;
  parentPath: string;
  tagsQuery: {
    isLoading: boolean;
    error: unknown;
    data: { items: TagItemVM[] } | undefined;
  };
  sourcesQuery: {
    isLoading: boolean;
    error: unknown;
    data: SourceVM[] | undefined;
  };
  colorTagOptions: Array<{ label: string; value: ColorTagValue }>;
  fileTypeOptions: Array<{ label: string; value: FileType }>;
  canChooseTags: boolean;
  canChooseSources: boolean;
  formError: string | null;
  isFormPending: boolean;
  onNameChange: (value: string) => void;
  onFileTypeChange: (value: FileType | "") => void;
  onTagIdChange: (value: string) => void;
  onColorTagChange: (value: ColorTagValue | "") => void;
  onSourceIdChange: (value: string) => void;
  onParentPathChange: (value: string) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onCancelEdit: () => void;
}

export function CollectionForm({
  isEditingSelected,
  entryNote,
  name,
  fileType,
  tagId,
  colorTag,
  sourceId,
  parentPath,
  tagsQuery,
  sourcesQuery,
  colorTagOptions,
  fileTypeOptions,
  canChooseTags,
  canChooseSources,
  formError,
  isFormPending,
  onNameChange,
  onFileTypeChange,
  onTagIdChange,
  onColorTagChange,
  onSourceIdChange,
  onParentPathChange,
  onSubmit,
  onCancelEdit,
}: CollectionFormProps) {
  return (
    <form className="form-grid collections-form" onSubmit={onSubmit}>
      <div className="collections-form__header">
        <span className="page-header__eyebrow">
          {isEditingSelected ? t("features.collections.editCollection") : t("features.collections.createCollection")}
        </span>
        <p>
          {isEditingSelected
            ? t("features.collections.editDescription")
            : t("features.collections.createDescription")}
        </p>
      </div>
      {entryNote ? <div className="context-flow-note">{entryNote}</div> : null}

      <label className="field-stack">
        <span>{t("features.collections.name")}</span>
        <input
          className="text-input"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder={t("features.collections.namePlaceholder")}
        />
      </label>

      <label className="field-stack">
        <span>{t("common.labels.fileType")}</span>
        <select className="select-input" value={fileType} onChange={(event) => onFileTypeChange(event.target.value as FileType | "")}>
          <option value="">{t("features.collections.anyType")}</option>
          {fileTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="field-stack">
        <span>{t("common.labels.tag")}</span>
        <select
          className="select-input"
          value={tagId}
          onChange={(event) => onTagIdChange(event.target.value)}
          disabled={tagsQuery.isLoading || !canChooseTags}
        >
          <option value="">{t("features.collections.anyTag")}</option>
          {tagsQuery.data?.items.map((tag) => (
            <option key={tag.id} value={String(tag.id)}>
              {tag.name}
            </option>
          ))}
        </select>
      </label>

      {tagsQuery.error instanceof Error ? (
        <p className="collections-form__note">{t("features.collections.tagsUnavailableNote")}</p>
      ) : null}

      <label className="field-stack">
        <span>{t("common.labels.color")}</span>
        <select
          className="select-input"
          value={colorTag}
          onChange={(event) => onColorTagChange(event.target.value as ColorTagValue | "")}
        >
          <option value="">{t("common.colors.any")}</option>
          {colorTagOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="field-stack">
        <span>{t("common.labels.source")}</span>
        <select
          className="select-input"
          value={sourceId}
          onChange={(event) => {
            const nextSourceId = event.target.value;
            onSourceIdChange(nextSourceId);
            if (!nextSourceId) {
              onParentPathChange("");
            }
          }}
          disabled={sourcesQuery.isLoading || !canChooseSources}
        >
          <option value="">{t("features.collections.anySource")}</option>
          {sourcesQuery.data?.map((source) => (
            <option key={source.id} value={String(source.id)}>
              {source.display_name?.trim() || source.path}
            </option>
          ))}
        </select>
      </label>

      {sourcesQuery.error instanceof Error ? (
        <p className="collections-form__note">{t("features.collections.sourcesUnavailableNote")}</p>
      ) : null}

      <label className="field-stack">
        <span>{t("common.labels.parentPath")}</span>
        <input
          className="text-input"
          value={parentPath}
          onChange={(event) => onParentPathChange(event.target.value)}
          placeholder={t("features.collections.parentPathPlaceholder")}
          disabled={!sourceId}
        />
      </label>

      {formError ? <p className="collections-form__error">{formError}</p> : null}

      <div className="collections-form__actions">
        <button className="primary-button" type="submit" disabled={isFormPending}>
          {isFormPending
            ? t("common.actions.saving")
            : isEditingSelected
              ? t("common.actions.updateCollection")
              : t("common.actions.createCollection")}
        </button>
        {isEditingSelected ? (
          <button className="secondary-button" type="button" onClick={onCancelEdit}>
            {t("common.actions.switchToCreate")}
          </button>
        ) : null}
      </div>
    </form>
  );
}
