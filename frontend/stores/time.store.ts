/**
 * Time Store - Phase 10a.2
 * 
 * Manages business clock, time offset, and time-travel state
 * Enables viewing train positions at past or future moments
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface TimeStore {
  // Business clock from backend (UNIX timestamp or ISO string)
  businessClock: Date;
  setBusinessClock: (clock: Date) => void;

  // Time offset in milliseconds (negative = past, positive = future)
  timeOffset: number; // milliseconds
  setTimeOffset: (offset: number) => void;

  // Custom time mode (e.g., time picker modal)
  customTimeEnabled: boolean;
  customTime: Date | null;
  setCustomTime: (time: Date | null) => void;
  setCustomTimeEnabled: (enabled: boolean) => void;

  // Reset to current time
  resetToNow: () => void;

  // Compute effective display time
  displayTime: () => Date;
}

/**
 * useTimeStore - Time and time-travel state
 * 
 * Populated by:
 * - Phase 10a.8: API response includes latest businessClock
 * - Phase 10a.5: TimeControls component updates timeOffset
 * 
 * Used by:
 * - Phase 10a.5: Polling coordinator (reads displayTime for tile ID)
 * - Phase 10a.3: TimeControls component (updates timeOffset)
 * - Phase 10a.6: Train filtering (filters by displayTime)
 */
export const useTimeStore = create<TimeStore>()(
  subscribeWithSelector((set, get) => ({
    // Business clock from backend
    businessClock: new Date(),
    setBusinessClock: (clock) => set({ businessClock: clock }),

    // Time offset for past/future viewing
    timeOffset: 0,
    setTimeOffset: (offset) => set({ timeOffset: offset }),

    // Custom time picker
    customTimeEnabled: false,
    customTime: null,
    setCustomTime: (time) => set({ customTime: time }),
    setCustomTimeEnabled: (enabled) => set({ customTimeEnabled: enabled }),

    // Reset to current business clock
    resetToNow: () =>
      set({
        timeOffset: 0,
        customTimeEnabled: false,
        customTime: null,
      }),

    // Compute effective display time
    displayTime: () => {
      const state = get();
      if (state.customTimeEnabled && state.customTime) {
        return state.customTime;
      }
      return new Date(state.businessClock.getTime() + state.timeOffset);
    },
  }))
);

// Selectors for efficient re-renders (Phase 10a.5)
export const selectBusinessClock = (state: TimeStore) => state.businessClock;
export const selectTimeOffset = (state: TimeStore) => state.timeOffset;
export const selectDisplayTime = (state: TimeStore) => state.displayTime();
export const selectCustomTimeEnabled = (state: TimeStore) => state.customTimeEnabled;
