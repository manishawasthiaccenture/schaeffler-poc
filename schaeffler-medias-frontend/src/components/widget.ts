// Shared props for every side-panel widget. `send` posts a follow-up message
// (e.g. a chip action) back through the orchestrator. Pass { silent: true } for
// UI control actions (cart edits, show cart) that shouldn't appear in the chat.
// Pass { intent } for a proposal topic drill-down (answered directly by topic id).
export type SendOptions = { silent?: boolean; intent?: string | null };

export type SendFn = (
  message: string,
  payload?: Record<string, unknown> | null,
  opts?: SendOptions,
) => void;

export interface WidgetProps<T = unknown> {
  data: T;
  send: SendFn;
}
