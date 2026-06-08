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
