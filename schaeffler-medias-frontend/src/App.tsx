import { useEffect, useRef, useState } from "react";
import { TopBar } from "./shell/TopBar";
import { SubHeader, type MenuItem } from "./shell/SubHeader";
import { Landing } from "./shell/Landing";
import { ChatInput } from "./shell/ChatInput";
import { renderWidget } from "./components/registry";
import type { SendOptions } from "./components/widget";
import { createConversation } from "./api/client";
import { sendMessage } from "./api/sse";
import type { CartData, UIPayload } from "./types/contract";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

// Clickable quick-reply chips shown in the chat, keyed by the current workflow step.
const SUGGESTIONS: Record<string, string[]> = {
  greeting: ["I want to buy products"],
  confirmed: ["Place another order", "View order details"],
};

// Messages that start a fresh order — clear the local cart badge optimistically.
const RESET_MESSAGES = new Set([
  "i want to buy products",
  "place another order",
  "start over",
  "new order",
]);

// The five landing intents, also available from the hamburger menu.
const MENU: MenuItem[] = [
  { key: "buy", label: "Buy products", message: "I want to buy products" },
  { key: "certificates", label: "Certificates", message: "Certificates" },
  { key: "support", label: "Support", message: "Support" },
  { key: "order", label: "Order status", message: "Order" },
  { key: "price", label: "Price & Availability", message: "Price & Availability" },
];
const MENU_KEY_BY_MESSAGE = new Map(MENU.map((m) => [m.message.toLowerCase(), m.key]));

export default function App() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [panel, setPanel] = useState<UIPayload[]>([]);
  const [sending, setSending] = useState(false);
  const [step, setStep] = useState<string>("greeting");
  const [cartCount, setCartCount] = useState(0);
  const [activeMenu, setActiveMenu] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createConversation()
      .then(setConversationId)
      .catch(() => setError("Could not connect to the medias backend. Is it running on the API base URL?"));
  }, []);

  function resetToHome() {
    setMessages([]);
    setPanel([]);
    setStep("greeting");
    setCartCount(0);
    setActiveMenu("");
    setConversationId(null);
    createConversation()
      .then(setConversationId)
      .catch(() => setError("Could not connect to the medias backend. Is it running on the API base URL?"));
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(message: string, payload: Record<string, unknown> | null = null, opts: SendOptions = {}) {
    if (!conversationId || sending || !message.trim()) return;
    const silent = !!opts.silent;
    const lower = message.trim().toLowerCase();

    if (RESET_MESSAGES.has(lower)) setCartCount(0);
    if (MENU_KEY_BY_MESSAGE.has(lower)) setActiveMenu(MENU_KEY_BY_MESSAGE.get(lower)!);

    setSending(true);
    if (!silent) {
      setMessages((prev) => [...prev, { role: "user", text: message }, { role: "assistant", text: "" }]);
    }

    let assistantText = "";
    const incomingUi: UIPayload[] = [];

    const setAssistant = (text: string) => {
      if (silent) return;
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", text };
        return next;
      });
    };

    try {
      await sendMessage(conversationId, message, payload, {
        onText: (chunk) => {
          assistantText += chunk;
          setAssistant(assistantText);
        },
        onUi: (p) => {
          incomingUi.push(p);
          if (p.component === "Cart") setCartCount((p.data as CartData).item_count);
        },
        onDone: (turnStep) => {
          if (incomingUi.length) setPanel(incomingUi);
          setStep(turnStep);
        },
      });
    } catch {
      setAssistant("Sorry, something went wrong talking to the assistant.");
    } finally {
      setSending(false);
    }
  }

  const started = messages.length > 0;
  const suggestions = started ? SUGGESTIONS[step] ?? [] : [];

  return (
    <div className="h-full w-full flex items-center justify-center p-4">
      <div className="w-full max-w-6xl h-[92vh] bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col">
        <TopBar onClose={resetToHome} />
        <SubHeader
          menu={MENU}
          activeMenu={activeMenu}
          onSelectMenu={(item) => send(item.message)}
          cartCount={cartCount}
          onShowCart={() => send("show cart", null, { silent: true })}
        />
        {error && <div className="bg-red-50 text-red-700 text-sm px-6 py-2">{error}</div>}

        {!started ? (
          <Landing onSend={send} disabled={sending || !conversationId} />
        ) : (
          <div className="flex-1 min-h-0 grid grid-cols-2">
            <section className="flex flex-col min-h-0 border-r border-gray-200">
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-3">
                {messages.map((m, i) => (
                  <MessageBubble key={i} role={m.role} text={m.text} />
                ))}
              </div>
              {suggestions.length > 0 && (
                <div className="px-6 pb-2 flex flex-wrap gap-2">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      disabled={sending}
                      className="border border-schaeffler-green text-schaeffler-green text-sm rounded-full px-3 py-1 hover:bg-schaeffler-greenLight disabled:opacity-40"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              <ChatInput onSend={send} disabled={sending} />
            </section>

            <section className="overflow-y-auto p-6 bg-gray-50">
              {panel.length === 0 ? (
                <p className="text-sm text-gray-400">The assistant's results will appear here.</p>
              ) : (
                <div className="space-y-4">
                  {panel.map((p, i) => (
                    <div key={i}>{renderWidget(p, send)}</div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ role, text }: ChatMessage) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
          isUser ? "bg-schaeffler-green text-white" : "bg-white border border-gray-200 text-gray-800"
        }`}
      >
        {text || (isUser ? "" : "…")}
      </div>
    </div>
  );
}
