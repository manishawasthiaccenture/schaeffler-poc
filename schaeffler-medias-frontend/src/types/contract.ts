// TypeScript mirror of the backend UI payload contract (PRD §10 / app/tools.py).

export type UIComponentName =
  | "UploadWidget"
  | "TypePrompt"
  | "MappingTable"
  | "QuoteCard"
  | "Cart"
  | "CheckoutForm"
  | "Confirmation"
  | "ProductDetails"
  | "EquivalentPrompt"
  | "AlreadyInCart"
  | "StubMessage"
  | "SlideDeck";

export interface UIPayload<T = unknown> {
  component: UIComponentName;
  data: T;
}

export interface UploadWidgetData {
  enabled: boolean;
  title: string;
  button: string;
  note: string;
}

export interface TypePromptData {
  placeholder: string;
}

export type MappingStatus = "matched" | "mapped" | "no_equivalent";

export interface MappingRow {
  raw: string;
  matched_sku: string | null;
  status: MappingStatus;
  confidence: number;
  qty: number;
}

export interface MappingTableData {
  rows: MappingRow[];
  actions: string[];
}

export interface QuoteLineData {
  sku: string;
  description: string;
  qty: number;
  unit_price: string;
  unit_price_display: string;
  line_total: string;
  line_total_display: string;
}

export interface QuoteCardData {
  quote_id: string;
  status: string;
  currency: string;
  total: string;
  total_display: string;
  valid_until: string;
  lines: QuoteLineData[];
  actions: string[];
}

export interface CartItemData {
  sku: string;
  description: string;
  qty: number;
  unit_price: string;
  unit_price_display: string;
  line_total: string;
  line_total_display: string;
}

export interface CartData {
  items: CartItemData[];
  item_count: number;
  total_qty: number;
  total: string;
  total_display: string;
  actions: string[];
}

export interface CheckoutFormData {
  fields: {
    purchase_order_number: { label: string; required: boolean; max_length: number };
    order_type: { label: string; type: string; options: string[] };
    comment: { label: string; required: boolean; max_length: number };
  };
  sections: string[];
  actions: string[];
}

export interface ConfirmationData {
  order_id: string;
  status: string;
  message: string;
}

export interface ProductDetailsData {
  sku: string;
  description: string;
  category: string;
  in_stock: boolean;
  lead_time_days: number;
  price_tiers: { range: string; unit_price_display: string }[];
  from_price_display: string | null;
  attributes: Record<string, string | number | boolean>;
}

export interface EquivalentPromptData {
  raw: string;
  sku: string;
  description: string;
}

export interface AlreadyInCartData {
  sku: string;
  description: string;
  current_qty: number;
}

export interface StubMessageData {
  title: string;
  message: string;
}

// Proposal Q&A: slides shown in the side panel for an RFQ topic.
// `image` is the served image stem (e.g. "orals-6"); see GET /slides/{image}.jpg.
export interface SlideData {
  image: string;
  label: string;
}

export interface SlideDeckData {
  slides: SlideData[];
}

// A clickable suggestion chip. `intent` is set for proposal topic drill-downs
// (posted back as the `intent` field); follow-up questions send `message` as text.
export interface Suggestion {
  label: string;
  message: string;
  intent: string | null;
}

// Which engine produced a turn — drives chip handling and rich-text rendering.
export type TurnMode = "order" | "proposal";

export type SSEEvent =
  | { type: "text"; text: string }
  | { type: "ui"; payload: UIPayload }
  | { type: "done"; step: string; mode?: TurnMode; suggestions?: Suggestion[] };
