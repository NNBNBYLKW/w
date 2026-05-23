import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listBrowseCards, type BrowseV2Response } from "../../../services/api/browseV2Api";

const PAGE_SIZE = 50;

export function useBrowseV2Cards(params: {
  domain: string;
  category?: string;
  storage_state: string;
  card_kind: string;
  page: number;
}) {
  const queryParams = useMemo(() => ({
    domain: params.domain,
    category: params.category || undefined,
    storage_state: params.storage_state,
    card_kind: params.card_kind,
    page: params.page,
    page_size: PAGE_SIZE,
  }), [params.domain, params.category, params.storage_state, params.card_kind, params.page]);

  const { data, isLoading, isError, error } = useQuery<BrowseV2Response>({
    queryKey: ["browse-v2", queryParams],
    queryFn: () => listBrowseCards(queryParams),
  });

  const items = data?.items ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return { data, isLoading, isError, error, items, totalPages };
}
