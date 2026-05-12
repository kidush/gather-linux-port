// Stub for gather-native-desktop-utils (macOS-only native module)
// This module provides window management helpers that are only implemented
// for macOS. Place this file at:
//   extracted/node_modules/gather-native-desktop-utils/index.js
// before repacking the app.asar.

module.exports = {
  GetWindowInfoById: () => ({}),
  MoveWindowBelowWindowById: () => {},
  MoveAllWindowsBelowTargetWindow: () => {},
  HideCursor: () => {},
  ShowCursor: () => {},
};
