import type { Suggestion } from "../types/contract";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const apiBase = API_BASE;

export async function createConversation(): Promise<string> {
  const res = await fetch(`${API_BASE}/conversations`, { method: "POST" });
  if (!res.ok) throw new Error(`failed to create conversation: ${res.status}`);
  const data = (await res.json()) as { conversation_id: string };
  return data.conversation_id;
}

export function quotePdfUrl(quoteId: string): string {
  return `${API_BASE}/quotes/${encodeURIComponent(quoteId)}/pdf`;
}

// Proposal slide image (served by the backend; may 404 -> SlideDeck shows a placeholder).
export function slideUrl(image: string): string {
  return `${API_BASE}/slides/${encodeURIComponent(image)}.jpg`;
}

export interface Welcome {
  text: string;
  suggestions: Suggestion[];
}

// Landing greeting + starter questions for the proposal Q&A.
export async function getWelcome(): Promise<Welcome> {
  const res = await fetch(`${API_BASE}/welcome`);
  if (!res.ok) throw new Error(`failed to load welcome: ${res.status}`);
  return (await res.json()) as Welcome;
}
