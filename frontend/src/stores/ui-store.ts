import { create } from 'zustand';

export type AddModalMode = 'form' | 'paste';

interface UIStore {
  // Modal states
  isAddModalOpen: boolean;
  addModalMode: AddModalMode;
  isEditModalOpen: boolean;
  editingApplicationId: string | null;

  // Command Palette
  isCommandPaletteOpen: boolean;

  // Sidebar
  isSidebarCollapsed: boolean;

  // Actions
  openAddModal: (mode?: AddModalMode) => void;
  openPasteModal: () => void;
  closeAddModal: () => void;
  openEditModal: (id: string) => void;
  closeEditModal: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleCommandPalette: () => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isAddModalOpen: false,
  addModalMode: 'form',
  isEditModalOpen: false,
  editingApplicationId: null,
  isCommandPaletteOpen: false,
  isSidebarCollapsed: false,

  openAddModal: (mode = 'form') => set({ isAddModalOpen: true, addModalMode: mode }),
  openPasteModal: () => set({ isAddModalOpen: true, addModalMode: 'paste' }),
  closeAddModal: () => set({ isAddModalOpen: false, addModalMode: 'form' }),

  openEditModal: (id) => set({ isEditModalOpen: true, editingApplicationId: id }),
  closeEditModal: () => set({ isEditModalOpen: false, editingApplicationId: null }),

  openCommandPalette: () => set({ isCommandPaletteOpen: true }),
  closeCommandPalette: () => set({ isCommandPaletteOpen: false }),
  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),

  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));
