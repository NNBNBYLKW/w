import { useState } from "react";
import { t } from "../../shared/text";
import { getObjectTypeGroups, objectTypeLabel } from "../library/objectTypeOptions";
import type { BrowseV2LooseFileCard } from "../../services/api/browseV2Api";
import type { LibraryRootVM } from "../../services/api/libraryObjectsApi";
import { suggestCollectionName, suggestTypeForFiles } from "./composeHelpers";

interface Props {
  selectedFiles: BrowseV2LooseFileCard[];
  roots: LibraryRootVM[];
  selectionSS: string;
  onCancel: () => void;
  onConfirm: (params: {
    inbox_item_ids?: number[];
    file_ids?: number[];
    object_name: string;
    suggested_object_type?: string;
    target_library_root_id?: number;
  }) => void;
  busy: boolean;
}

export function ComposeObjectModal({ selectedFiles, roots, selectionSS, onCancel, onConfirm, busy }: Props) {
  const defaultName = suggestCollectionName(selectedFiles.map(f => f.name));
  const defaultType = suggestTypeForFiles(selectedFiles.map(f => ({ name: f.name })));
  const defaultRootId = roots.find(r => r.is_default)?.id ?? roots[0]?.id ?? null;

  const [objectName, setObjectName] = useState(defaultName);
  const [objectType, setObjectType] = useState(defaultType);
  const [targetRootId, setTargetRootId] = useState<number | null>(defaultRootId);

  const enabledRoots = roots.filter(r => r.is_enabled);

  function handleConfirm() {
    if (!objectName.trim()) return;
    if (selectionSS === "inbox") {
      onConfirm({
        inbox_item_ids: selectedFiles.map(f => f.inbox_item_id!).filter(id => id != null),
        object_name: objectName.trim(),
        suggested_object_type: objectType || undefined,
        target_library_root_id: targetRootId ?? undefined,
      });
    } else {
      onConfirm({
        file_ids: selectedFiles.map(f => f.file_id),
        object_name: objectName.trim(),
        suggested_object_type: objectType || undefined,
        target_library_root_id: targetRootId ?? undefined,
      });
    }
  }

  return (
    <div className="library-inbox-modal-overlay" onClick={busy ? undefined : onCancel}>
      <div className="library-inbox-modal" role="dialog" onClick={e => e.stopPropagation()} style={{maxWidth:520}}>
        <h3>{t("features.browseV2.compose.title")}</h3>
        <p className="library-inbox-modal-hint">{t("features.browseV2.compose.description")}</p>
        <div className="library-review-form" style={{marginTop:12}}>
          <div className="library-review-form__field">
            <label>{t("features.browseV2.compose.objectName")}</label>
            <input type="text" value={objectName} onChange={e => setObjectName(e.target.value)} disabled={busy} style={{width:"100%",padding:"4px 8px"}} />
          </div>
          <div className="library-review-form__field">
            <label>{t("features.library.inbox.review.finalObjectType")}</label>
            <select value={objectType} onChange={e => setObjectType(e.target.value)} disabled={busy}>
              <option value="">— {t("features.library.inbox.review.selectType")} —</option>
              {getObjectTypeGroups().map(group => (
                <optgroup key={group.groupKey} label={t(group.groupKey as Parameters<typeof t>[0])}>
                  {group.options.map(opt => <option key={opt.value} value={opt.value}>{objectTypeLabel(opt.value)}</option>)}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="library-review-form__field">
            <label>{t("features.library.inbox.review.targetRoot")}</label>
            {enabledRoots.length > 0 ? (
              <select value={targetRootId ?? ""} onChange={e => setTargetRootId(e.target.value ? Number(e.target.value) : null)} disabled={busy}>
                <option value="">— {t("features.library.inbox.review.selectRoot")} —</option>
                {enabledRoots.map(r => <option key={r.id} value={r.id}>{r.display_name || r.root_path}</option>)}
              </select>
            ) : (
              <span className="library-review-form__hint">{t("features.library.inbox.review.noRoots")}</span>
            )}
          </div>
        </div>
        <div className="browse-v2-compose-preview" style={{maxHeight:150,overflowY:"auto",margin:"8px 0",fontSize:12,border:"1px solid #e0e0e0",borderRadius:4,padding:4}}>
          <strong>{selectedFiles.length} {t("features.browseV2.compose.selectedFiles")}:</strong>
          {selectedFiles.map((f, i) => (
            <div key={i} style={{whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}} title={f.name}>{f.name}</div>
          ))}
        </div>
        {selectionSS === "inbox" ? (
          <p className="library-review-notice">{t("features.browseV2.compose.safety")}</p>
        ) : (
          <p className="library-review-notice">{t("features.browseV2.compose.safetyExternal")}</p>
        )}
        <div className="library-inbox-modal-actions">
          <button className="secondary-button" type="button" onClick={onCancel} disabled={busy}>{t("features.library.inbox.cancel")}</button>
          <button className="primary-button" type="button" disabled={!objectName.trim() || busy} onClick={handleConfirm}>
            {busy ? "…" : t("features.browseV2.compose.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
