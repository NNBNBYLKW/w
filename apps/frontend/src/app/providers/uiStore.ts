import { create } from "zustand";


type ToastItem = {
  id: string;
  message: string;
};

type UIStore = {
  selectedItemId: string | null;
  isDetailsPanelOpen: boolean;
  theme: "dark";
  toasts: ToastItem[];
  selectItem: (id: string | null) => void;
  setDetailsPanelOpen: (isOpen: boolean) => void;
  pushToast: (message: string) => void;
  removeToast: (id: string) => void;
};


export const useUIStore = create<UIStore>((set) => ({
  selectedItemId: null,
  isDetailsPanelOpen: true,
  theme: "dark",
  toasts: [],
  selectItem: (id) => set({ selectedItemId: id }),
  setDetailsPanelOpen: (isOpen) => set({ isDetailsPanelOpen: isOpen }),
  pushToast: (message) =>
    set((state) => ({
      toasts: [...state.toasts, { id: crypto.randomUUID(), message }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));
