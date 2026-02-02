import { create } from 'zustand';

interface UIStore {
  // Modal states
  isAddModalOpen: boolean;
  isEditModalOpen: boolean;
  editingApplicationId: string | null;
  
  // Command Palette
  isCommandPaletteOpen: boolean;
  
  // Sidebar
  isSidebarCollapsed: boolean;
  
  // Actions
  openAddModal: () => void;
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
  isEditModalOpen: false,
  editingApplicationId: null,
  isCommandPaletteOpen: false,
  isSidebarCollapsed: false,

  openAddModal: () => set({ isAddModalOpen: true }),
  closeAddModal: () => set({ isAddModalOpen: false }),
  
  openEditModal: (id) => set({ isEditModalOpen: true, editingApplicationId: id }),
  closeEditModal: () => set({ isEditModalOpen: false, editingApplicationId: null }),
  
  openCommandPalette: () => set({ isCommandPaletteOpen: true }),
  closeCommandPalette: () => set({ isCommandPaletteOpen: false }),
  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),
  
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));
