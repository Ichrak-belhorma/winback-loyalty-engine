import type { Flow } from "./api";

export const FLOW_COLORS: Record<Flow, string> = {
  welcome: "#2f6fed",
  winback: "#d9480f",
  review: "#2b8a3e",
  referral: "#7048e8",
};

export const SEGMENT_COLORS: Record<string, string> = {
  champions: "#2b8a3e",
  loyal: "#2f6fed",
  new: "#7048e8",
  at_risk: "#e67700",
  hibernating: "#868e96",
};
