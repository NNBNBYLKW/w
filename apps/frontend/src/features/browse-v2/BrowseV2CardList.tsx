import { useRef, useState, useCallback, useMemo, useEffect } from "react";

import type {
  BrowseV2Card,
  BrowseV2LooseFileCard,
  BrowseV2ObjectCard,
} from "../../services/api/browseV2Api";
import { t } from "../../shared/text";
import { useVirtualList } from "../../shared/hooks/useVirtualList";
import { LooseFileCard } from "./LooseFileCard";
import { ObjectCard } from "./ObjectCard";

export interface BrowseV2CardListProps {
  showObjects: boolean;
  showLooseFiles: boolean;
  objectCards: BrowseV2ObjectCard[];
  looseFileCards: BrowseV2LooseFileCard[];
  hasData: boolean;
  selectedObject: BrowseV2ObjectCard | null;
  selectedItemId: string | null;
  selectedFileIds: Set<number>;
  onCardClick: (card: BrowseV2Card, event?: { ctrlKey?: boolean; shiftKey?: boolean }) => void;
  onCheckboxToggle: (card: BrowseV2LooseFileCard) => void;
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  allSelected?: boolean;
}

export function BrowseV2CardList({
  showObjects,
  showLooseFiles,
  objectCards,
  looseFileCards,
  hasData,
  selectedObject,
  selectedItemId,
  selectedFileIds,
  onCardClick,
  onCheckboxToggle,
  onSelectAll,
  onClearSelection,
  allSelected = false,
}: BrowseV2CardListProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const cardContainerRef = useRef<HTMLDivElement>(null);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  // B16: Compute average item height based on card types
  const objCount = objectCards.length;
  const fileCount = looseFileCards.length;
  const totalCardCount = objCount + fileCount;
  const avgHeight = totalCardCount > 0
    ? Math.round((objCount * 80 + fileCount * 60) / totalCardCount)
    : 80;

  const { startIndex, endIndex, offsetY, totalHeight, onScroll } = useVirtualList(
    cardContainerRef,
    { itemHeight: avgHeight, totalItems: totalCardCount },
  );

  const allCards = useMemo(
    () => [...(showObjects ? objectCards : []), ...(showLooseFiles ? looseFileCards : [])],
    [showObjects, showLooseFiles, objectCards, looseFileCards],
  );
  const visibleCards = allCards.slice(startIndex, endIndex);
  const visibleObjectCards = visibleCards.filter(
    (c): c is BrowseV2ObjectCard => c.card_kind === "object",
  );
  const visibleLooseFileCards = visibleCards.filter(
    (c): c is BrowseV2LooseFileCard => c.card_kind === "loose_file",
  );

  // C4: Arrow key navigation (roving tabindex)
  const handleKeyDown = useCallback((e: React.KeyboardEvent, index: number) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(index + 1, allCards.length - 1);
      setFocusedIndex(next);
      onCardClick(allCards[next]);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(index - 1, 0);
      setFocusedIndex(prev);
      onCardClick(allCards[prev]);
    } else if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      onCardClick(allCards[index]);
    }
  }, [allCards, onCardClick]);

  // C3: Handle click with modifiers for multi-select
  const handleCardClick = useCallback((card: BrowseV2Card, event?: { ctrlKey?: boolean; shiftKey?: boolean }) => {
    onCardClick(card, event);
  }, [onCardClick]);

  // C1: Right-click context menu
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; card: BrowseV2Card } | null>(null);
  const handleContextMenu = useCallback((e: React.MouseEvent, card: BrowseV2Card) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, card });
  }, []);
  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => { window.removeEventListener("click", close); window.removeEventListener("scroll", close, true); };
  }, [contextMenu]);

  const handleContextAction = useCallback((action: string) => {
    if (!contextMenu) return;
    const card = contextMenu.card;
    if (action === "view-details") {
      onCardClick(card);
    } else if (action === "open-file" && card.card_kind === "loose_file") {
      // TODO: implement open file via IPC
    } else if (action === "show-in-folder" && card.card_kind === "loose_file") {
      // TODO: implement show in folder via IPC
    } else if (action === "add-to-collection") {
      // TODO: implement add to collection
    }
    setContextMenu(null);
  }, [contextMenu, onCardClick]);

  if (!hasData || allCards.length === 0) {
    return null;
  }

  return (
    <div ref={cardContainerRef} onScroll={onScroll} style={{ height: "100%", overflow: "auto" }}>
      <div style={{ height: totalHeight, position: "relative" }}>
        <div style={{ position: "absolute", top: offsetY, width: "100%" }}>
          <div className="browse-v2-result-sections">
            {showObjects && (objectCards.length === 0 || visibleObjectCards.length > 0) ? (
              <section className="browse-v2-result-section">
                <header className="browse-v2-result-section__header">
                  <div>
                    <span className="workbench-eyebrow">{t("features.browseV2.badges.object")}</span>
                    <h4>{t("features.browseV2.sections.objects")}</h4>
                  </div>
                  <span>{t("features.browseV2.sections.currentPageCount", { count: String(objectCards.length) })}</span>
                </header>
                {objectCards.length > 0 ? (
                  <div className="browse-v2-card-grid browse-v2-card-grid--objects">
                    {visibleObjectCards.map((card, idx) => (
                      <ObjectCard
                        key={card.namespaced_id}
                        card={card}
                        selected={selectedObject?.namespaced_id === card.namespaced_id}
                        onClick={() => handleCardClick(card)}
                        onContextMenu={(e) => handleContextMenu(e, card)}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="browse-v2-result-section__empty">{t("features.browseV2.sections.noObjectsOnPage")}</p>
                )}
              </section>
            ) : null}
            {showLooseFiles && (looseFileCards.length === 0 || visibleLooseFileCards.length > 0) ? (
              <section className="browse-v2-result-section">
                <header className="browse-v2-result-section__header">
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {/* B13: Select All checkbox */}
                    {onSelectAll && (
                      <label className="browse-v2-card__check" onClick={(e) => e.stopPropagation()}>
                        <input
                          className="browse-v2-card__check-input"
                          type="checkbox"
                          checked={allSelected}
                          onChange={() => allSelected ? onClearSelection?.() : onSelectAll()}
                          tabIndex={0}
                          aria-label={t("features.browseV2.selectAll")}
                        />
                      </label>
                    )}
                    <div>
                      <span className="workbench-eyebrow">{t("features.browseV2.badges.file")}</span>
                      <h4>{t("features.browseV2.sections.looseFiles")}</h4>
                    </div>
                  </div>
                  <span>{t("features.browseV2.sections.currentPageCount", { count: String(looseFileCards.length) })}</span>
                </header>
                {looseFileCards.length > 0 ? (
                  <div className="browse-v2-file-list">
                    {visibleLooseFileCards.map((card) => (
                      <LooseFileCard
                        key={`f${card.file_id}`}
                        card={card}
                        selected={selectedItemId === String(card.file_id)}
                        checked={selectedFileIds.has(card.file_id)}
                        onCheckboxToggle={
                          card.storage_state === "inbox" || card.storage_state === "external" || card.storage_state === "managed"
                            ? () => onCheckboxToggle(card)
                            : undefined
                        }
                        onClick={() => handleCardClick(card)}
                        isHovered={hoveredId === card.file_id}
                        onMouseEnter={() => setHoveredId(card.file_id)}
                        onMouseLeave={() => setHoveredId(null)}
                        onContextMenu={(e) => handleContextMenu(e, card)}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="browse-v2-result-section__empty">{t("features.browseV2.sections.noLooseFilesOnPage")}</p>
                )}
              </section>
            ) : null}
          </div>
        </div>
      </div>
      {/* C1: Right-click context menu */}
      {contextMenu && (
        <div
          className="browse-v2-context-menu"
          style={{ position: "fixed", left: contextMenu.x, top: contextMenu.y, zIndex: 9999 }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="browse-v2-context-menu__item" onClick={() => handleContextAction("view-details")}>View details</button>
          {contextMenu.card.card_kind === "loose_file" && (
            <>
              <button className="browse-v2-context-menu__item" onClick={() => handleContextAction("open-file")}>Open file</button>
              <button className="browse-v2-context-menu__item" onClick={() => handleContextAction("show-in-folder")}>Show in folder</button>
            </>
          )}
          <button className="browse-v2-context-menu__item" onClick={() => handleContextAction("add-to-collection")}>Add to collection</button>
        </div>
      )}
    </div>
  );
}
