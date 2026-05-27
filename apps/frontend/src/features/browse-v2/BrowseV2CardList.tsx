import { useRef } from "react";

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
  onCardClick: (card: BrowseV2Card) => void;
  onCheckboxToggle: (card: BrowseV2LooseFileCard) => void;
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
}: BrowseV2CardListProps) {
  const totalCardCount = objectCards.length + looseFileCards.length;
  const cardContainerRef = useRef<HTMLDivElement>(null);
  const { startIndex, endIndex, offsetY, totalHeight, onScroll } = useVirtualList(
    cardContainerRef,
    { itemHeight: 80, totalItems: totalCardCount },
  );
  const allCards = [...(showObjects ? objectCards : []), ...(showLooseFiles ? looseFileCards : [])];
  const visibleCards = allCards.slice(startIndex, endIndex);
  const visibleObjectCards = visibleCards.filter(
    (c): c is BrowseV2ObjectCard => c.card_kind === "object",
  );
  const visibleLooseFileCards = visibleCards.filter(
    (c): c is BrowseV2LooseFileCard => c.card_kind === "loose_file",
  );

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
                    {visibleObjectCards.map((card) => (
                      <ObjectCard
                        key={card.namespaced_id}
                        card={card}
                        selected={selectedObject?.namespaced_id === card.namespaced_id}
                        onClick={() => onCardClick(card)}
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
                  <div>
                    <span className="workbench-eyebrow">{t("features.browseV2.badges.file")}</span>
                    <h4>{t("features.browseV2.sections.looseFiles")}</h4>
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
                        onClick={() => onCardClick(card)}
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
    </div>
  );
}
