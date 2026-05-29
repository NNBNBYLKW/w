import { useState } from "react";
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
  const [page, setPage] = useState(1);

  function setScope(nextDomain: DomainValue, nextCategory = "") {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set("domain", nextDomain);
      if (nextCategory) { next.set("category", nextCategory); }
      else { next.delete("category"); }
      return next;
    }, { replace: true });
    setPage(1);
  }

  function updateFilter(key: string, value: string) {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (value && value !== "all") { next.set(key, value); }
      else { next.delete(key); }
      return next;
    }, { replace: true });
    setPage(1);
  }

  return { domain, category, storageState, cardKind, sort, order, page, setPage, setScope, updateFilter };
}
