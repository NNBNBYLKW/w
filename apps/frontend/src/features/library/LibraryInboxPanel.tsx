import { useCallback, useEffect, useMemo, useState } from "react";

import { t } from "../../shared/text";
import { hasDesktopFilePicker, selectImportFiles, selectImportFolder } from "../../services/desktop/filePicker";
import {
  confirmInboxItem, confirmObjectCandidate, createCandidateFromInboxItem,
  createCandidateFromObjectCandidate, createImportBatch, generateDraftPlan,
  getObjectCandidate, importFilesToBatch, importFolderToBatch,
  listImportBatches, listInboxItems, listObjectCandidates,
  rejectInboxItem, rejectObjectCandidate, updateInboxItem,
  type ImportBatchVM, type ImportFilesResponse, type ImportFolderResponse,
  type InboxItemVM, type ObjectCandidateDetailVM, type ObjectCandidateMemberVM,
  type ObjectCandidateVM,
} from "../../services/api/importingApi";
import { listLibraryRoots, type LibraryRootVM } from "../../services/api/libraryObjectsApi";

// ── helpers ──────────────────────────────────────────────

type ImportMode = "files" | "folder-as-object" | "folder-as-loose";

const OBJECT_TYPE_OPTIONS = [
  "movie", "clip", "course", "anime", "video_collection", "clip_set", "movie_collection",
  "game", "software", "imgset", "comic", "photo_event", "web_image_set", "docset",
] as const;

function objectTypeLabel(ot: string): string {
  const key = `features.library.inbox.objectTypes.${ot}`;
  return t(key as Parameters<typeof t>[0]) || ot;
}

function batchStatusLabel(status: string): string {
  return t(`features.library.inbox.batchStatus.${status}` as Parameters<typeof t>[0]) || status;
}

function itemStatusLabel(status: string): string {
  return t(`features.library.inbox.itemStatus.${status}` as Parameters<typeof t>[0]) || status;
}

function isEmptyCreatedBatch(batch: ImportBatchVM): boolean {
  return batch.file_count === 0 && batch.status === "created";
}

function roleLabel(role: string): string {
  return t(`features.library.inbox.objectCandidates.roles.${role}` as Parameters<typeof t>[0]) || role;
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
  const [roots, setRoots] = useState<LibraryRootVM[]>([]);

  // review form state (per-card)
  const [reviewStates, setReviewStates] = useState<Record<number, {
    finalType: string; targetRootId: number | null; launchFileId: number | null;
    candidateId?: number; planId?: number; busy: boolean;
  }>>({});
  const pageSize = 20;

  function getReviewState(id: number) {
    return reviewStates[id] || { finalType: "", targetRootId: null, launchFileId: null, busy: false };
  }
  function updateReviewState(id: number, patch: Partial<ReturnType<typeof getReviewState>>) {
    setReviewStates(prev => ({ ...prev, [id]: { ...getReviewState(id), ...patch } }));
  }

  // load roots
  const loadRoots = useCallback(async () => {
    try { setRoots(await listLibraryRoots()); } catch { /* non-critical */ }
  }, []);
  useEffect(() => { loadRoots(); }, [loadRoots]);

  const enabledRoots = useMemo(() => roots.filter(r => r.is_enabled), [roots]);
  const enabledRootOptions = useMemo(() => enabledRoots.map(r => ({
    value: r.id, label: `${r.display_name || r.root_path} (${r.root_path})`,
  })), [enabledRoots]);

  async function loadBatches() {
    setLoading(true); setError(null);
    try { setBatches((await listImportBatches(1, 50)).items); }
    catch { setError(t("features.library.inbox.errors.loadFailed")); }
    finally { setLoading(false); }
  }

  async function loadItems(batchId: number | null, p = 1) {
    setLoading(true); setError(null);
    try { const r = await listInboxItems(p, pageSize, undefined, batchId ?? undefined); setItems(r.items); setTotalItems(r.total); setPage(p); }
    catch { setError(t("features.library.inbox.errors.loadFailed")); }
    finally { setLoading(false); }
  }

  async function loadObjectCandidates() {
    try { setObjectCandidates((await listObjectCandidates(1, 100)).items); }
    catch { /* non-critical */ }
  }

  async function doImportFilePaths(paths: string[]) {
    if (paths.length === 0) return;
    setImporting(true); setImportResult(null); setError(null);
    try { const batch = await createImportBatch(); const r = await importFilesToBatch(batch.id, paths); setImportResult(r); await loadBatches(); await loadItems(batch.id); setSelectedBatchId(batch.id); }
    catch (err) { setError(String(err)); } finally { setImporting(false); }
  }

  async function doImportFolderPath(folderPath: string) {
    setImporting(true); setImportResult(null); setError(null);
    try { const batch = await createImportBatch(); const r = await importFolderToBatch(batch.id, [folderPath], mode === "folder-as-object" ? "object" : "loose_files"); setImportResult(r); await loadBatches(); await loadObjectCandidates(); setSelectedBatchId(batch.id); }
    catch (err) { setError(String(err)); } finally { setImporting(false); }
  }

  async function handleChooseFiles() {
    setImportResult(null);
    const paths = await selectImportFiles();
    if (paths.length > 0) await doImportFilePaths(paths);
    else if (!hasDesktopFilePicker()) setShowPathModal(true);
  }

  async function handleChooseFolder() {
    setImportResult(null);
    const fp = await selectImportFolder();
    if (fp) await doImportFolderPath(fp);
    else if (!hasDesktopFilePicker()) setShowPathModal(true);
  }

  async function handleCreateBatch() {
    setError(null);
    try { await createImportBatch(); await loadBatches(); } catch { setError(t("features.library.inbox.errors.batchCreateFailed")); }
  }

  async function handleExpandCandidate(candidateId: number) {
    try { setExpandedCandidate(await getObjectCandidate(candidateId)); }
    catch { /* ignore */ }
    // init review state from suggestion
    const oc = objectCandidates.find(o => o.id === candidateId);
    if (oc) {
      updateReviewState(candidateId, {
        finalType: oc.final_object_type || oc.suggested_object_type || "",
        targetRootId: (oc as Record<string, unknown>).target_library_root_id as number | null ?? null,
        launchFileId: oc.launch_file_id,
      });
    }
  }

  // ── Review actions ──────────────────────────────────────

  async function handleConfirmObjectCandidate(ocId: number) {
    const rs = getReviewState(ocId);
    if (!rs.finalType || !rs.targetRootId) return;
    updateReviewState(ocId, { busy: true });
    try {
      await confirmObjectCandidate(ocId, { final_object_type: rs.finalType, target_library_root_id: rs.targetRootId, launch_file_id: rs.launchFileId ?? undefined });
      await loadObjectCandidates();
    } catch (err) { setError(String(err)); }
    finally { updateReviewState(ocId, { busy: false }); }
  }

  async function handleRejectObjectCandidate(ocId: number) {
    updateReviewState(ocId, { busy: true });
    try { await rejectObjectCandidate(ocId); await loadObjectCandidates(); }
    catch (err) { setError(String(err)); }
    finally { updateReviewState(ocId, { busy: false }); }
  }

  async function handleCreateCandidateFromOC(ocId: number) {
    updateReviewState(ocId, { busy: true });
    try {
      const r = await createCandidateFromObjectCandidate(ocId);
      updateReviewState(ocId, { candidateId: r.candidate_id });
      await loadObjectCandidates();
    } catch (err) { setError(String(err)); }
    finally { updateReviewState(ocId, { busy: false }); }
  }

  async function handleGeneratePlanFromOC(ocId: number) {
    const rs = getReviewState(ocId);
    if (!rs.candidateId) return;
    updateReviewState(ocId, { busy: true });
    try {
      const r = await generateDraftPlan([rs.candidateId]);
      updateReviewState(ocId, { planId: r.plan_id });
      await loadObjectCandidates();
    } catch (err) { setError(String(err)); }
    finally { updateReviewState(ocId, { busy: false }); }
  }

  // inbox item review
  async function handleConfirmInboxItem(itemId: number) {
    const rs = getReviewState(itemId);
    if (!rs.finalType || !rs.targetRootId) return;
    updateReviewState(itemId, { busy: true });
    try { await confirmInboxItem(itemId, { final_object_type: rs.finalType, target_library_root_id: rs.targetRootId }); await loadBatches(); await loadItems(selectedBatchId); }
    catch (err) { setError(String(err)); }
    finally { updateReviewState(itemId, { busy: false }); }
  }

  async function handleRejectInboxItem(itemId: number) {
    updateReviewState(itemId, { busy: true });
    try { await rejectInboxItem(itemId); await loadItems(selectedBatchId); }
    catch (err) { setError(String(err)); }
    finally { updateReviewState(itemId, { busy: false }); }
  }

  async function handleCreateCandidateFromItem(itemId: number) {
    updateReviewState(itemId, { busy: true });
    try { const r = await createCandidateFromInboxItem(itemId); updateReviewState(itemId, { candidateId: r.candidate_id }); await loadItems(selectedBatchId); }
    catch (err) { setError(String(err)); }
    finally { updateReviewState(itemId, { busy: false }); }
  }

  async function handleGeneratePlanFromItem(itemId: number) {
    const rs = getReviewState(itemId);
    if (!rs.candidateId) return;
    updateReviewState(itemId, { busy: true });
    try { const r = await generateDraftPlan([rs.candidateId]); updateReviewState(itemId, { planId: r.plan_id }); await loadItems(selectedBatchId); }
    catch (err) { setError(String(err)); }
    finally { updateReviewState(itemId, { busy: false }); }
  }

  // ── Path modal ─────────────────────────────────────────

  function handlePathModalConfirm() {
    const paths = pathInput.split("\n").map(s => s.trim()).filter(s => s.length > 0);
    setShowPathModal(false); setPathInput("");
    if (paths.length > 0) doImportFilePaths(paths);
  }

  useEffect(() => { loadBatches(); loadObjectCandidates(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.ceil(totalItems / pageSize);

  return (
    <div className="library-inbox-panel">
      {/* ── Toolbar ── */}
      <div className="library-inbox-toolbar">
        <div className="library-inbox-mode-picker" role="radiogroup" aria-label="Import mode">
          {(["files", "folder-as-object", "folder-as-loose"] as const).map(val => (
            <button key={val} className={`secondary-button settings-segmented-button${mode === val ? " settings-segmented-button--selected" : ""}`} type="button" role="radio" aria-checked={mode === val} onClick={() => setMode(val)}>
              {t(`features.library.inbox.importModes.${val === "files" ? "files" : val === "folder-as-object" ? "folderAsObject" : "folderAsLoose"}` as Parameters<typeof t>[0])}
            </button>
          ))}
        </div>
        {mode === "files" ? (
          <button className="primary-button" type="button" onClick={handleChooseFiles} disabled={importing}>{importing ? "…" : t("features.library.inbox.importFiles")}</button>
        ) : (
          <button className="primary-button" type="button" onClick={handleChooseFolder} disabled={importing}>{importing ? "…" : t("features.library.inbox.importModes.folderAsObject")}</button>
        )}
        <button className="secondary-button" type="button" onClick={handleCreateBatch} disabled={importing}>{t("features.library.inbox.createBatch")}</button>
        <button className="secondary-button" type="button" onClick={() => setShowPathModal(true)} disabled={importing}>{t("features.library.inbox.enterPathsManually")}</button>
        <span className="library-inbox-hint">{t("features.library.inbox.importModes.folderHint")}</span>
      </div>

      {error && <div className="library-inbox-error" role="alert">{error}</div>}
      {importResult && (
        <div className="library-inbox-result">
          {"created_items" in importResult && <p>Imported: {importResult.created_items.length} / Failed: {importResult.failed_items.length}</p>}
          {"object_candidates" in importResult && importResult.object_candidates.length > 0 && <p>Object candidates created: {importResult.object_candidates.length}</p>}
          {"failed_items" in importResult && importResult.failed_items.length > 0 && <ul>{importResult.failed_items.map((f, i) => <li key={i}>{f.path}: {f.error}</li>)}</ul>}
        </div>
      )}

      {showPathModal && (
        <div className="library-inbox-modal-overlay" onClick={() => { setShowPathModal(false); setPathInput(""); }}>
          <div className="library-inbox-modal" role="dialog" onClick={e => e.stopPropagation()}>
            <h3>{t("features.library.inbox.pathModalTitle")}</h3>
            <p className="library-inbox-modal-hint">{t("features.library.inbox.pathModalHint")}</p>
            <textarea className="library-inbox-modal-textarea" rows={8} value={pathInput} onChange={e => setPathInput(e.target.value)} placeholder={t("features.library.inbox.pathModalPlaceholder")} />
            <div className="library-inbox-modal-actions">
              <button className="secondary-button" type="button" onClick={() => { setShowPathModal(false); setPathInput(""); }}>{t("features.library.inbox.cancel")}</button>
              <button className="primary-button" type="button" disabled={!pathInput.trim()} onClick={handlePathModalConfirm}>{t("features.library.inbox.import")}</button>
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
              const rs = getReviewState(oc.id);
              const groups = isExpanded ? groupMembers(expandedCandidate.members) : {};
              const canConfirm = !!rs.finalType && !!rs.targetRootId && oc.status !== "confirmed" && oc.status !== "planned" && oc.status !== "organized" && oc.status !== "rejected";
              const canCreateCandidate = oc.status === "confirmed" && !rs.candidateId;
              const canGeneratePlan = !!rs.candidateId && !rs.planId;

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
                    {oc.launch_file_id && <span className="library-object-card__launch">{t("features.library.inbox.review.launchCandidate")}: <span className="library-badge library-badge--suggestion">{t("features.library.inbox.review.suggested")}</span></span>}
                    {rs.candidateId && <span className="library-badge library-badge--success">{t("features.library.inbox.review.candidateCreated").replace("#{id}", String(rs.candidateId))}</span>}
                    {rs.planId && <span className="library-badge library-badge--info">{t("features.library.inbox.review.planGenerated").replace("#{id}", String(rs.planId))}</span>}
                  </div>

                  {/* Review form (always visible on expanded) */}
                  {isExpanded && oc.status !== "rejected" && oc.status !== "organized" && (
                    <div className="library-object-card__review">
                      <h4 className="library-object-card__review-title">{t("features.library.inbox.review.title")}</h4>
                      <div className="library-review-form">
                        <div className="library-review-form__field">
                          <label>{t("features.library.inbox.review.finalObjectType")}</label>
                          <select value={rs.finalType} onChange={e => updateReviewState(oc.id, { finalType: e.target.value })} disabled={rs.busy}>
                            <option value="">— {t("features.library.inbox.review.selectType")} —</option>
                            {OBJECT_TYPE_OPTIONS.map(ot => <option key={ot} value={ot}>{objectTypeLabel(ot)}</option>)}
                          </select>
                          {oc.suggested_object_type && oc.suggested_object_type !== rs.finalType && (
                            <span className="library-review-form__suggestion">← {t("features.library.inbox.review.suggested")}: {objectTypeLabel(oc.suggested_object_type)}</span>
                          )}
                        </div>
                        <div className="library-review-form__field">
                          <label>{t("features.library.inbox.review.targetRoot")}</label>
                          {enabledRootOptions.length > 0 ? (
                            <select value={rs.targetRootId ?? ""} onChange={e => updateReviewState(oc.id, { targetRootId: e.target.value ? Number(e.target.value) : null })} disabled={rs.busy}>
                              <option value="">— {t("features.library.inbox.review.selectRoot")} —</option>
                              {enabledRootOptions.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                            </select>
                          ) : (
                            <span className="library-review-form__hint">{t("features.library.inbox.review.noRoots")}</span>
                          )}
                        </div>
                        <div className="library-review-form__field">
                          <label>{t("features.library.inbox.review.launchCandidate")}</label>
                          <select value={rs.launchFileId ?? ""} onChange={e => updateReviewState(oc.id, { launchFileId: e.target.value ? Number(e.target.value) : null })} disabled={rs.busy}>
                            <option value="">— {t("features.library.inbox.review.launchCandidate")} —</option>
                            {expandedCandidate.members.filter(m => m.role === "launch_exe" || m.role === "support_exe" || m.role === "installer").map(m => (
                              <option key={m.file_id} value={m.file_id ?? ""}>{m.source_path?.split(/[\\/]/).pop() || `#${m.file_id}`} ({roleLabel(m.role)})</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="library-review-actions">
                        <button className="primary-button" type="button" disabled={!canConfirm || rs.busy} onClick={() => handleConfirmObjectCandidate(oc.id)}>
                          {t("features.library.inbox.review.confirm")}
                        </button>
                        <button className="secondary-button" type="button" disabled={rs.busy || oc.status === "rejected"} onClick={() => handleRejectObjectCandidate(oc.id)}>
                          {t("features.library.inbox.review.reject")}
                        </button>
                        <button className="secondary-button" type="button" disabled={!canCreateCandidate || rs.busy} onClick={() => handleCreateCandidateFromOC(oc.id)}>
                          {t("features.library.inbox.review.createCandidate")}
                        </button>
                        <button className="secondary-button" type="button" disabled={!canGeneratePlan || rs.busy} onClick={() => handleGeneratePlanFromOC(oc.id)}>
                          {t("features.library.inbox.review.generatePlan")}
                        </button>
                      </div>
                      <p className="library-review-notice">{t("features.library.inbox.review.draftOnly")}</p>
                      {rs.planId && (
                        <p className="library-review-link">
                          <a href={`#/library?tab=plans`}>{t("features.library.inbox.review.viewPlan")} (#{rs.planId})</a>
                        </p>
                      )}
                    </div>
                  )}

                  {/* Member groups */}
                  {isExpanded && Object.keys(ROLE_GROUPS).map(g => {
                    const gMembers = groups[g] || [];
                    if (gMembers.length === 0) return null;
                    return (
                      <div key={g} className="library-object-card__member-group">
                        <h4 className="library-object-card__group-title">{t(`features.library.inbox.objectCandidates.memberGroups.${g}` as Parameters<typeof t>[0])} ({gMembers.length})</h4>
                        <ul className="library-object-card__member-list">
                          {gMembers.map(m => (
                            <li key={m.id} className="library-object-card__member">
                              <span className="library-object-card__member-role">{roleLabel(m.role)}</span>
                              <span className="library-object-card__member-path" title={m.source_path || ""}>{m.source_path?.split(/[\\/]/).pop() || m.inbox_path?.split(/[\\/]/).pop() || `#${m.inbox_item_id}`}</span>
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
          <table className="library-table"><thead><tr><th>ID</th><th>Status</th><th>Files</th><th>Created</th></tr></thead>
            <tbody>{batches.map(batch => (
              <tr key={batch.id} className={selectedBatchId === batch.id ? "library-table-row--selected" : ""} onClick={() => { setSelectedBatchId(batch.id); loadItems(batch.id); }} style={{ cursor: "pointer" }}>
                <td>#{batch.id}</td>
                <td><span className={`library-status-pill library-status--${batch.status}`}>{batchStatusLabel(batch.status)}</span>{isEmptyCreatedBatch(batch) && <span className="library-inbox-empty-batch-hint"> — {t("features.library.inbox.emptyBatchHint")}</span>}</td>
                <td>{batch.completed_count}/{batch.file_count}{batch.failed_count > 0 && <span className="library-inbox-warning"> ({batch.failed_count} failed)</span>}</td>
                <td>{batch.created_at ? new Date(batch.created_at).toLocaleString() : "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {/* ── Inbox items ── */}
      {items.length > 0 && (
        <div className="library-inbox-items">
          <h3 className="library-section-title">{t("features.library.inbox.tabs.items")}{selectedBatchId != null && ` (Batch #${selectedBatchId})`}</h3>
          <table className="library-table"><thead><tr><th>ID</th><th>{t("features.library.inbox.columns.sourcePath")}</th><th>{t("features.library.inbox.columns.inboxPath")}</th><th>{t("features.library.inbox.columns.status")}</th><th>{t("features.library.inbox.columns.detectedType")}</th><th></th></tr></thead>
            <tbody>{items.map(item => {
              const rs = getReviewState(item.id);
              const canConfirm = !!rs.finalType && !!rs.targetRootId && item.status !== "classified" && item.status !== "planned" && item.status !== "organized" && item.status !== "rejected";
              const canCreateCandidate = item.status === "classified" && !rs.candidateId;
              const canGeneratePlan = !!rs.candidateId && !rs.planId;
              return (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td className="library-inbox-path" title={item.source_path}>{item.source_path}</td>
                  <td className="library-inbox-path" title={item.inbox_path}>{item.inbox_path}</td>
                  <td><span className={`library-status-pill library-status--${item.status}`}>{itemStatusLabel(item.status)}</span>{rs.candidateId && <span className="library-badge library-badge--success" style={{marginLeft:4}}>#{rs.candidateId}</span>}{rs.planId && <span className="library-badge library-badge--info" style={{marginLeft:4}}>P#{rs.planId}</span>}</td>
                  <td>{item.detected_object_type || item.detected_file_kind || "—"}</td>
                  <td>
                    {(item.status === "imported" || item.status === "pending_review" || item.status === "classified") && item.status !== "rejected" && (
                      <div className="library-inbox-item-review" style={{display:"flex",gap:4,flexWrap:"wrap"}}>
                        <select value={rs.finalType} onChange={e => updateReviewState(item.id, { finalType: e.target.value })} style={{width:100}} disabled={rs.busy}>
                          <option value="">—</option>
                          {OBJECT_TYPE_OPTIONS.map(ot => <option key={ot} value={ot}>{objectTypeLabel(ot)}</option>)}
                        </select>
                        <select value={rs.targetRootId ?? ""} onChange={e => updateReviewState(item.id, { targetRootId: e.target.value ? Number(e.target.value) : null })} style={{width:140}} disabled={rs.busy}>
                          <option value="">— root —</option>
                          {enabledRootOptions.map(r => <option key={r.value} value={r.value}>{r.display_name || r.root_path}</option>)}
                        </select>
                        <button className="secondary-button" type="button" disabled={!canConfirm || rs.busy} onClick={() => handleConfirmInboxItem(item.id)} style={{fontSize:11}}>{t("features.library.inbox.review.confirm")}</button>
                        <button className="secondary-button" type="button" disabled={rs.busy} onClick={() => handleRejectInboxItem(item.id)} style={{fontSize:11}}>{t("features.library.inbox.review.reject")}</button>
                        <button className="secondary-button" type="button" disabled={!canCreateCandidate || rs.busy} onClick={() => handleCreateCandidateFromItem(item.id)} style={{fontSize:11}}>+Candidate</button>
                        <button className="secondary-button" type="button" disabled={!canGeneratePlan || rs.busy} onClick={() => handleGeneratePlanFromItem(item.id)} style={{fontSize:11}}>+Plan</button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}</tbody>
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
