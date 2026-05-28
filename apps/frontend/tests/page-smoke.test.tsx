import { describe, test, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

// Mock browse API
vi.mock("../src/services/api/browseV2Api", () => ({
  listBrowseCards: vi.fn().mockResolvedValue({
    items: [], page: 1, total_pages: 1, total: 0, object_count: 0, loose_file_count: 0, summary: null,
  }),
  getBrowseObjectDetail: vi.fn().mockResolvedValue({ object: null, members: [], loose_files: [] }),
}));

vi.mock("../src/services/api/searchApi", () => ({
  searchFiles: vi.fn().mockResolvedValue({ items: [], page: 1, total_pages: 1, total_items: 0 }),
}));

vi.mock("../src/services/api/tagsApi", () => ({
  listTags: vi.fn().mockResolvedValue({ items: [] }),
  listFilesForTag: vi.fn().mockResolvedValue({ items: [], page: 1, total_pages: 1, total_items: 0 }),
  deleteTagApi: vi.fn().mockResolvedValue(undefined),
  mergeTags: vi.fn().mockResolvedValue(undefined),
  renameTag: vi.fn().mockResolvedValue(undefined),
  TagsApiError: class extends Error {
    code: string | null;
    constructor(message: string, code: string | null = null) {
      super(message);
      this.name = "TagsApiError";
      this.code = code;
    }
  },
}));

function Wrapper({ children, route = "/" }: { children: React.ReactNode; route?: string }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("BrowseV2Page", () => {
  test("renders without crashing", async () => {
    const BrowseV2Page = (await import("../src/pages/browse-v2/BrowseV2Page")).default;
    render(<BrowseV2Page />, { wrapper: (p: any) => <Wrapper {...p} route="/browse-v2?domain=media" /> });
    const browseElements = screen.getAllByText(/Browse/i);
    expect(browseElements.length).toBeGreaterThan(0);
  });
});

describe("SearchPage", () => {
  test("renders search input", async () => {
    const SearchPage = (await import("../src/pages/search/SearchPage")).default;
    render(<SearchPage />, { wrapper: (p: any) => <Wrapper {...p} route="/search" /> });
    expect(screen.getByPlaceholderText(/Search/i)).toBeInTheDocument();
  });
});

describe("TagsPage", () => {
  test("renders tag view", async () => {
    const { TagsPage } = await import("../src/pages/tags/TagsPage");
    render(<TagsPage />, { wrapper: (p: any) => <Wrapper {...p} route="/tags" /> });
    const tagElements = screen.getAllByText(/Tags/i);
    expect(tagElements.length).toBeGreaterThan(0);
  });
});
