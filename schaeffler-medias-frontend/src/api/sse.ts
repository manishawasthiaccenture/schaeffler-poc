import { apiBase } from "./client";
import type { SSEEvent, TurnMode, UIPayload, Suggestion } from "../types/contract";

export interface DoneInfo {
  step: string;
  mode: TurnMode;
  suggestions: Suggestion[];
}

export interface StreamHandlers {
  onText?: (text: string) => void;
  onUi?: (payload: UIPayload) => void;
  onDone?: (info: DoneInfo) => void;
}

export interface SendExtras {
  // Proposal sub-option chip click: posts the topic id so the backend answers it directly.
  intent?: string | null;
}

// POSTs a message and parses the Server-Sent Events stream from the response body.
// (EventSource only supports GET, so we read the stream manually.)
export async function sendMessage(
  conversationId: string,
  message: string,
  payload: Record<string, unknown> | null,
  handlers: StreamHandlers,
  extras: SendExtras = {},
): Promise<void> {
  const res = await fetch(`${apiBase}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, payload, intent: extras.intent ?? null }),
  });
  if (!res.ok || !res.body) throw new Error(`message failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!block.startsWith("data:")) continue;

      const event = JSON.parse(block.slice("data:".length).trim()) as SSEEvent;
      if (event.type === "text") handlers.onText?.(event.text);
      else if (event.type === "ui") handlers.onUi?.(event.payload);
      else if (event.type === "done")
        handlers.onDone?.({
          step: event.step,
          mode: event.mode ?? "order",
          suggestions: event.suggestions ?? [],
        });
    }
  }
}
