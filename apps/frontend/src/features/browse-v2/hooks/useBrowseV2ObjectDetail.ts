import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBrowseObjectDetail, type BrowseV2ObjectCard } from "../../../services/api/browseV2Api";

const PAGE_SIZE = 50;

export function useBrowseV2ObjectDetail(selectedObject: BrowseV2ObjectCard | null) {
  const [memberPage, setMemberPage] = useState(1);

  useEffect(() => {
    setMemberPage(1);
  }, [selectedObject?.object_source, selectedObject?.source_id]);

  const { data: objectDetail, isLoading: objectDetailLoading, isError: objectDetailError } = useQuery({
    queryKey: ["browse-v2-obj-detail", selectedObject?.object_source, selectedObject?.source_id, memberPage],
    queryFn: () => getBrowseObjectDetail({
      object_source: selectedObject!.object_source,
      source_id: selectedObject!.source_id,
      member_page: memberPage,
      member_page_size: PAGE_SIZE,
    }),
    enabled: selectedObject !== null,
  });

  return { objectDetail, objectDetailLoading, objectDetailError, memberPage, setMemberPage };
}
