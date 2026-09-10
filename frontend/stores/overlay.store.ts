/**
 * Overlay Store — OPUS-5 map shell.
 *
 * The map is the permanent main content. Two kinds of overlays open over it:
 *
 *   - RIBBON tools (top ribbon)  → 50% width panel (right side)
 *   - SIDEBAR areas (left rail)  → full-content panel (covers the map)
 *
 * Only one overlay is open at a time. `null` = map only (no overlay).
 */
import { create } from "zustand";

export type OverlayKind = "ribbon" | "sidebar";

export interface OverlayState {
  /** The overlay id (e.g. "layers", "plan", "blocks"), or null for none. */
  active: string | null;
  kind: OverlayKind | null;
  open: (id: string, kind: OverlayKind) => void;
  close: () => void;
  toggle: (id: string, kind: OverlayKind) => void;
}

export const useOverlayStore = create<OverlayState>((set, get) => ({
  active: null,
  kind: null,
  open: (id, kind) => set({ active: id, kind }),
  close: () => set({ active: null, kind: null }),
  toggle: (id, kind) => {
    const { active } = get();
    if (active === id) set({ active: null, kind: null });
    else set({ active: id, kind });
  },
}));
