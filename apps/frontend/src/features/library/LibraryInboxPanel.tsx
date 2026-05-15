import { useEffect, useState } from "react";

import { t } from "../../shared/text";
import {
  hasDesktopFilePicker,
  selectImportFiles,
  selectImportFolder,
} from "../../services/desktop/filePicker";
import {
  createImportBatch,
  getObjectCandidate,
  importFilesToBatch,
  importFolderToBatch,
  listImportBatches,
  listInboxItems,
  listObjectCandidates,
  type ImportBatchVM,
  type ImportFilesResponse,
  type ImportFolderResponse,
  type InboxItemVM,
  type ObjectCandidateDetailVM,
  type ObjectCandidateMemberVM,
  type ObjectCandidateVM,
} from "../../services/api/importingApi";

// ── helpers ──────────────────────────────────────────────

type ImportMode = "files" | "folder-as-object" | "folder-as-loose";

function batchStatusLabel(status: string): string {
  const key = `features.library.inbox.batchStatus.${status}`;
  return t(key as Parameters<typeof t>[0]) || status;
}

function itemStatusLabel(status: string): string {
  const key = `features.library.inbox.itemStatus.${status}`;
  return t(key as Parameters<typeof t>[0]) || status;
}

function isEmptyCreatedBatch(batch: ImportBatchVM): boolean {
  return batch.file_count === 0 && batch.status === "created";
}

function roleLabel(role: string): string {
  const key = `features.library.inbox.objectCandidates.roles.${role}`;
  return t(key as Parameters<typeof t>[0]) || role;
}

const ROLE_GROUPS: Record<string, string[]> = {
  launch: ["launch_exe"],
  videos: ["main_video", "episode_video"],
  images: ["image_member", "cover"],
  documents: ["document_attachment", "subtitle", "config"],
  components: ["support_exe", "installer", "uninstaller", "component", "component_dll", "asset", "asset_dir", "plugin_dir"],
  unknown: ["unknown_child"],
};

function groupMembers(members: ObjectCandidateMemberVM[]): Record<string, ObjectCandidateMemberVM[]> {
  const groups: Record<string, ObjectCandidateMemberVM[]> = {};
  for (const g of Object.keys(ROLE_GROUPS)) groups[g] = [];
  for (const m of members) {
    let placed = false;
    for (const [g, roles] of Object.entries(ROLE_GROUPS)) {
      if (roles.includes(m.role)) { groups[g].push(m); placed = true; break; }
    }
    if (!placed) groups["unknown"].push(m);
  }
  return groups;
}

// ── Component ────────────────────────────────────────────

export function LibraryInboxPanel() {
  const [batches, setBatches] = useState<ImportBatchVM[]>([]);
  const [items, setItems] = useState<InboxItemVM[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportFilesResponse | ImportFolderResponse | null>(null);
  const [page, setPage] = useState(1);
  const [showPathModal, setShowPathModal] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [mode, setMode] = useState<ImportMode>("files");
  const [objectCandidates, setObjectCandidates] = useState<ObjectCandidateVM[]>([]);
  const [expandedCandidate, setExpandedCandidate] = useState<ObjectCandidateDetailVM | null>(null);
  const pageSize = 20;

  async function loadBatches() {
    setLoading(true); setError(null);
    try { setBatches((await listImportBatches(1, 50)).items); }
    catch { setError(t("features.library.inbox.errors.loadFailed")); }
    finally { setLoading(false); }
  }

  async function loadItems(batchId: number | null, p = 1) {
    setLoading(true); setError(null);
    try {
      const r = await listInboxItems(p, pageSize, undefined, batchId ?? undefined);
      setItems(r.items); setTotalItems(r.total); setPage(p);
    } catch { setError(t("features.library.inbox.errors.loadFailed")); }
    finally { setLoading(false); }
  }

  async function loadObjectCandidates() {
    try { setObjectCandidates((await listObjectCandidates(1, 100)).items); }
    catch { /* non-critical */ }
  }

  async function doImportFilePaths(paths: string[]) {
    if (paths.length === 0) return;
    setImporting(true); setImportResult(null); setError(null);
    try {
      const batch = await createImportBatch();
      const r = await importFilesToBatch(batch.id, paths);
      setImportResult(r);
      await loadBatches(); await loadItems(batch.id);
      setSelectedBatchId(batch.id);
    } catch (err) { setError(String(err)); }
    finally { setImporting(false); }
  }

  async function doImportFolderPath(folderPath: string) {
    setImporting(true); setImportResult(null); setError(null);
    try {
      const batch = await createImportBatch();
      const r = await importFolderToBatch(
        batch.id, [folderPath],
        mode === "folder-as-object" ? "object" : "loose_files",
      );
      setImportResult(r);
      await loadBatches();
      await loadObjectCandidates();
      setSelectedBatchId(batch.id);
    } catch (err) { setError(String(err)); }
    finally { setImporting(false); }
  }

  // ── Primary actions ─────────────────────────────────────

  async function handleChooseFiles() {
    setImportResult(null);
    const paths = await selectImportFiles();
    if (paths.length > 0) { await doImportFilePaths(paths); }
    else if (!hasDesktopFilePicker()) { setShowPathModal(true); }
  }

  async function handleChooseFolder() {
    setImportResult(null);
    const folderPath = await selectImportFolder();
    if (folderPath) { await doImportFolderPath(folderPath); }
    else if (!hasDesktopFilePicker()) { setShowPathModal(true); }
  }

  async function handleCreateBatch() {
    setError(null);
    try { await createImportBatch(); await loadBatches(); }
    catch { setError(t("features.library.inbox.errors.batchCreateFailed")); }
  }

  async function handleExpandCandidate(candidateId: number) {
    try {
      const detail = await getObjectCandidate(candidateId);
      setExpandedCandidate(detail);
    } catch { /* ignore */ }
  }

  // ── Path modal ─────────────────────────────────────────

  function handlePathModalConfirm() {
    const paths = pathInput.split("\n").map(s => s.trim()).filter(s => s.length > 0);
    setShowPathModal(false); setPathInput("");
    if (paths.length > 0) doImportFilePaths(paths);
  }

  // ── Lifecycle ──────────────────────────────────────────

  useEffect(() => { loadBatches(); loadObjectCandidates(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.ceil(totalItems / pageSize);

  return (
    <div className="library-inbox-panel">
      {/* ── Toolbar ── */}
      <div className="library-inbox-toolbar">
        <div className="library-inbox-mode-picker" role="radiogroup" aria-label="Import mode">
          {([
            ["files", t("features.library.inbox.importModes.files")],
            ["folder-as-object", t("features.library.inbox.importModes.folderAsObject")],
            ["folder-as-loose", t("features.library.inbox.importModes.folderAsLoose")],
          ] as const).map(([val, label]) => (
            <button
              key={val}
              className={`secondary-button settings-segmented-button${mode === val ? " settings-segmented-button--selected" : ""}`}
              type="button"
              role="radio"
              aria-checked={mode === val}
              onClick={() => setMode(val)}
            >
              {label}
            </button>
          ))}
        </div>

        {mode === "files" ? (
          <button className="primary-button" type="button" onClick={handleChooseFiles} disabled={importing}>
            {importing ? "…" : t("features.library.inbox.importFiles")}
          </button>
        ) : (
          <button className="primary-button" type="button" onClick={handleChooseFolder} disabled={importing}>
            {importing ? "…" : t("features.library.inbox.importModes.folderAsObject")}
          </button>
        )}
        <button className="secondary-button" type="button" onClick={handleCreateBatch} disabled={importing}>
          {t("features.library.inbox.createBatch")}
        </button>
        <button className="secondary-button" type="button" onClick={() => setShowPathModal(true)} disabled={importing}>
          {t("features.library.inbox.enterPathsManually")}
        </button>
        <span className="library-inbox-hint">{t("features.library.inbox.importModes.folderHint")}</span>
      </div>

      {/* ── Error ── */}
      {error && <div className="library-inbox-error" role="alert">{error}</div>}

      {/* ── Import result ── */}
      {importResult && (
        <div className="library-inbox-result">
          {"created_items" in importResult && (
            <p>Imported: {importResult.created_items.length} / Failed: {importResult.failed_items.length}</p>
          )}
          {"object_candidates" in importResult && importResult.object_candidates.length > 0 && (
            <p>Object candidates created: {importResult.object_candidates.length}</p>
          )}
          {"failed_items" in importResult && importResult.failed_items.length > 0 && (
            <ul>{importResult.failed_items.map((f, i) => <li key={i}>{f.path}: {f.error}</li>)}</ul>
          )}
        </div>
      )}

      {/* ── Path modal ── */}
      {showPathModal && (
        <div className="library-inbox-modal-overlay" onClick={() => { setShowPathModal(false); setPathInput(""); }}>
          <div className="library-inbox-modal" role="dialog" onClick={e => e.stopPropagation()}>
            <h3>{t("features.library.inbox.pathModalTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.library.inbox.pathModalHint")}</p>
            <textarea className="library-inbox-modal-textarea" rows={8} value={pathInput}
              onChange={e => setPathInput(e.target.value)}
              placeholder={t("features.library.inbox.pathModalPlaceholder")} />
            <div className="library-inbox-modal-actions">
              <button className="secondary-button" type="button" onClick={() => { setShowPathModal(false); setPathInput(""); }}>
                {t("features.library.inbox.cancel")}
              </button>
              <button className="primary-button" type="button" disabled={!pathInput.trim()} onClick={handlePathModalConfirm}>
                {t("features.library.inbox.import")}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && <div className="library-inbox-loading" aria-live="polite">Loading...</div>}

      {!loading && batches.length === 0 && objectCandidates.length === 0 && items.length === 0 && (
        <div className="library-inbox-empty"><p>{t("features.library.inbox.empty")}</p></div>
      )}

      {/* ── Object Candidates ── */}
      {objectCandidates.length > 0 && (
        <div className="library-inbox-objects">
          <h3 className="library-section-title">{t("features.library.inbox.objectCandidates.title")}</h3>
          <div className="library-object-cards">
            {objectCandidates.map(oc => {
              const isExpanded = expandedCandidate?.id === oc.id;
              const groups = isExpanded ? groupMembers(expandedCandidate.members) : {};
              return (
                <div key={oc.id} className={`library-object-card${isExpanded ? " library-object-card--expanded" : ""}`}>
                  <div className="library-object-card__header" onClick={() => isExpanded ? setExpandedCandidate(null) : handleExpandCandidate(oc.id)} style={{ cursor: "pointer" }}>
                    <span className="library-object-card__name">{oc.inbox_root_path?.split(/[\\/]/).pop() || `#${oc.id}`}</span>
                    <span className={`library-status-pill library-status--${oc.status}`}>{oc.status}</span>
                    <span className="library-object-card__type">
                      {oc.suggested_object_type || "unknown"}
                      {oc.confidence && <span className="library-object-card__confidence"> ({oc.confidence})</span>}
                    </span>
                    <span className="library-object-card__count">{t("features.library.inbox.objectCandidates.memberCount").replace("{count}", String(oc.member_count))}</span>
                    {oc.launch_file_id && (
                      <span className="library-object-card__launch">
                        {t("features.library.inbox.objectCandidates.launchCandidate")}:{" "}
                        <span className="library-badge library-badge--suggestion">
                          {t("features.library.inbox.objectCandidates.launchSuggestion")}
                        </span>
                      </span>
                    )}
                  </div>
                  {isExpanded && Object.keys(ROLE_GROUPS).map(g => {
                    const gMembers = groups[g] || [];
                    if (gMembers.length === 0) return null;
                    const groupLabel = t(`features.library.inbox.objectCandidates.memberGroups.${g}` as Parameters<typeof t>[0]);
                    return (
                      <div key={g} className="library-object-card__member-group">
                        <h4 className="library-object-card__group-title">{groupLabel} ({gMembers.length})</h4>
                        <ul className="library-object-card__member-list">
                          {gMembers.map(m => (
                            <li key={m.id} className="library-object-card__member">
                              <span className="library-object-card__member-role">{roleLabel(m.role)}</span>
                              <span className="library-object-card__member-path" title={m.source_path || ""}>
                                {m.source_path?.split(/[\\/]/).pop() || m.inbox_path?.split(/[\\/]/).pop() || `#${m.inbox_item_id}`}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Batch list ── */}
      {batches.length > 0 && (
        <div className="library-inbox-batches">
          <h3 className="library-section-title">{t("features.library.inbox.tabs.batches")}</h3>
          <table className="library-table">
            <thead><tr><th>ID</th><th>Status</th><th>Files</th><th>Created</th></tr></thead>
            <tbody>
              {batches.map(batch => (
                <tr key={batch.id} className={selectedBatchId === batch.id ? "library-table-row--selected" : ""}
                  onClick={() => { setSelectedBatchId(batch.id); loadItems(batch.id); }}
                  style={{ cursor: "pointer" }}>
                  <td>#{batch.id}</td>
                  <td>
                    <span className={`library-status-pill library-status--${batch.status}`}>{batchStatusLabel(batch.status)}</span>
                    {isEmptyCreatedBatch(batch) && <span className="library-inbox-empty-batch-hint"> — {t("features.library.inbox.emptyBatchHint")}</span>}
                  </td>
                  <td>{batch.completed_count}/{batch.file_count}{batch.failed_count > 0 && <span className="library-inbox-warning"> ({batch.failed_count} failed)</span>}</td>
                  <td>{batch.created_at ? new Date(batch.created_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Inbox items ── */}
      {items.length > 0 && (
        <div className="library-inbox-items">
          <h3 className="library-section-title">{t("features.library.inbox.tabs.items")}{selectedBatchId != null && ` (Batch #${selectedBatchId})`}</h3>
          <table className="library-table">
            <thead><tr><th>ID</th><th>{t("features.library.inbox.columns.sourcePath")}</th><th>{t("features.library.inbox.columns.inboxPath")}</th><th>{t("features.library.inbox.columns.status")}</th><th>{t("features.library.inbox.columns.detectedType")}</th></tr></thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td className="library-inbox-path" title={item.source_path}>{item.source_path}</td>
                  <td className="library-inbox-path" title={item.inbox_path}>{item.inbox_path}</td>
                  <td><span className={`library-status-pill library-status--${item.status}`}>{itemStatusLabel(item.status)}</span></td>
                  <td>{item.detected_object_type || item.detected_file_kind || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="library-inbox-pagination">
              <button className="secondary-button" type="button" disabled={page <= 1} onClick={() => loadItems(selectedBatchId, page - 1)}>Previous</button>
              <span>Page {page} / {totalPages}</span>
              <button className="secondary-button" type="button" disabled={page >= totalPages} onClick={() => loadItems(selectedBatchId, page + 1)}>Next</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
