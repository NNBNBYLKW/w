import { create } from "zustand";


type ToastItem = {
  id: string;
  message: string;
};

type BatchSelectionSummary = {
  pageLabel: string;
  selectedCount: number;
};

type UIStore = {
  selectedItemId: string | null;
  isDetailsPanelOpen: boolean;
  isSidebarCollapsed: boolean;
  theme: "dark";
  toasts: ToastItem[];
  batchSelectionSummary: BatchSelectionSummary | null;
  selectItem: (id: string | null) => void;
  setDetailsPanelOpen: (isOpen: boolean) => void;
  setSidebarCollapsed: (isCollapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setBatchSelectionSummary: (summary: BatchSelectionSummary | null) => void;
  pushToast: (message: string) => void;
  removeToast: (id: string) => void;
};


export const useUIStore = create<UIStore>((set) => ({
  selectedItemId: null,
  isDetailsPanelOpen: true,
  isSidebarCollapsed: false,
  theme: "dark",
  toasts: [],
  batchSelectionSummary: null,
  selectItem: (id) => set({ selectedItemId: id }),
  setDetailsPanelOpen: (isOpen) => set({ isDetailsPanelOpen: isOpen }),
  setSidebarCollapsed: (isCollapsed) => set({ isSidebarCollapsed: isCollapsed }),
  toggleSidebarCollapsed: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  setBatchSelectionSummary: (summary) => set({ batchSelectionSummary: summary }),
  pushToast: (message) =>
    set((state) => ({
      toasts: [...state.toasts, { id: crypto.randomUUID(), message }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));
