import { useState, type FC } from "react";
import {
  SendIcon,
  MicIcon,
  AttachIcon,
  DocIcon,
  CartIcon,
  HelpIcon,
  WrenchIcon,
  ShuffleIcon,
} from "./icons";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

interface Card {
  title: string;
  subtitle: string;
  message: string;
  Icon: FC<{ className?: string }>;
}

// Five landing intents (storyboard frame 20). "Bulk Upload" is the ordering entry
// and posts "I want to buy products" (PRD D2); the rest route to coming-soon stubs.
const CARDS: Card[] = [
  { title: "Certificates", subtitle: "Request certificates for products", message: "Certificates", Icon: DocIcon },
  { title: "Bulk Upload", subtitle: "Quote & Order via file upload", message: "I want to buy products", Icon: CartIcon },
  { title: "Support", subtitle: "Get technical support", message: "Support", Icon: HelpIcon },
  { title: "Order", subtitle: "Check current status", message: "Order", Icon: WrenchIcon },
  {
    title: "Price & Availability",
    subtitle: "Check capacity & find alternatives",
    message: "Price & Availability",
    Icon: ShuffleIcon,
  },
];

export function Landing({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  function submit() {
    const value = text.trim();
    if (value) {
      onSend(value);
      setText("");
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-8 py-10">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-center text-4xl font-semibold text-gray-800">medias</h1>
        <p className="text-center text-gray-500 mt-2">
          Get instant answers about orders, products, and customer inquiries.
        </p>

        <div className="mt-8 flex items-center gap-3 border border-gray-300 rounded-full px-5 py-3 shadow-sm">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            disabled={disabled}
            placeholder="Ask me anything about products, orders or inquiries …"
            className="flex-1 outline-none text-sm disabled:opacity-50"
          />
          <MicIcon className="w-5 h-5 text-gray-300" />
          <AttachIcon className="w-5 h-5 text-gray-300" />
          <button
            onClick={submit}
            disabled={disabled}
            aria-label="Send"
            className="text-schaeffler-green disabled:opacity-40"
          >
            <SendIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-8 grid grid-cols-2 gap-4">
          {CARDS.map((card) => (
            <button
              key={card.title}
              onClick={() => onSend(card.message)}
              disabled={disabled}
              className="text-left border border-gray-200 rounded-lg p-4 flex gap-3 transition hover:border-schaeffler-green hover:shadow-sm disabled:opacity-50"
            >
              <span className="shrink-0 w-9 h-9 rounded bg-gray-100 flex items-center justify-center text-gray-600">
                <card.Icon className="w-5 h-5" />
              </span>
              <span>
                <span className="block font-medium text-gray-800">{card.title}</span>
                <span className="block text-sm text-gray-500">{card.subtitle}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
