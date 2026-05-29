import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import type { DomainValue } from "../../../shared/browse-taxonomy";

export function useBrowseV2SearchParams() {
  const [searchParams, setSearchParams] = useSearchParams();
  const domain = (searchParams.get("domain") as DomainValue) || "media";
  const category = searchParams.get("category") || "";
  const storageState = searchParams.get("storage") || "all";
  const cardKind = searchParams.get("kind") || "all";
  const sort = searchParams.get("sort") ?? "title";
  const order = searchParams.get("order") ?? "asc";
  const fileType = searchParams.get("fileType") || "";
  const needsReview = searchParams.get("needsReview") || "";
  const minConfidence = searchParams.get("minConfidence") || "";
  const dateFrom = searchParams.get("dateFrom") || "";
  const dateTo = searchParams.get("dateTo") || "";
  const minSize = searchParams.get("minSize") || "";
  const viewMode = (searchParams.get("view") as "grid" | "list" | "table") || "grid";
  const rawPage = searchParams.get("page");
  const page = rawPage ? Math.max(1, parseInt(rawPage, 10) || 1) : 1;
  const selected = searchParams.get("selected") || "";

  function setPage(nextPage: number) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (nextPage > 1) { next.set("page", String(nextPage)); }
      else { next.delete("page"); }
      return next;
    }, { replace: true });
  }

  function setScope(nextDomain: DomainValue, nextCategory = "") {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set("domain", nextDomain);
      if (nextCategory) { next.set("category", nextCategory); }
      else { next.delete("category"); }
      next.delete("page");
      return next;
    }, { replace: true });
  }

  const updateFilter = useCallback((key: string, value: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (value && value !== "all") { next.set(key, value); }
      else { next.delete(key); }
      next.delete("page");
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const clearAllFilters = useCallback(() => {
    setSearchParams(prev => {
      const next = new URLSearchParams();
      next.set("domain", prev.get("domain") || "media");
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  return {
    domain, category, storageState, cardKind, sort, order,
    fileType, needsReview, minConfidence, dateFrom, dateTo, minSize,
    viewMode, page, selected, setPage, setScope, updateFilter, clearAllFilters,
  };
}
