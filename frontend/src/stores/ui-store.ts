import { create } from 'zustand';

interface UIStore {
  // Modal states
  isAddModalOpen: boolean;
  isEditModalOpen: boolean;
  editingApplicationId: string | null;
  
  // Sidebar
  isSidebarCollapsed: boolean;
  
  // Actions
  openAddModal: () => void;
  closeAddModal: () => void;
  openEditModal: (id: string) => void;
  closeEditModal: () => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isAddModalOpen: false,
  isEditModalOpen: false,
  editingApplicationId: null,
  isSidebarCollapsed: false,

  openAddModal: () => set({ isAddModalOpen: true }),
  closeAddModal: () => set({ isAddModalOpen: false }),
  
  openEditModal: (id) => set({ isEditModalOpen: true, editingApplicationId: id }),
  closeEditModal: () => set({ isEditModalOpen: false, editingApplicationId: null }),
  
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));
