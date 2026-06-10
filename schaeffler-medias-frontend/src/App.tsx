import { useEffect, useRef, useState } from "react";
import { TopBar } from "./shell/TopBar";
import { SubHeader, type MenuItem } from "./shell/SubHeader";
import { Landing } from "./shell/Landing";
import { ChatInput } from "./shell/ChatInput";
import { renderWidget } from "./components/registry";
import type { SendOptions } from "./components/widget";
import { createConversation } from "./api/client";
import { sendMessage } from "./api/sse";
import type { CartData, Suggestion, UIPayload } from "./types/contract";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  // Proposal answers may contain light HTML (bold key phrases); rendered as rich text.
  html?: boolean;
}

// A resolved chat suggestion chip: a label plus what happens when it's clicked.
interface Chip {
  label: string;
  onClick: () => void;
}

// Special chip labels that are handled client-side instead of posting to the backend.
const HOME_LABEL = "Back to home";
const MAIN_SCREEN_LABEL = "Go to main screen";
const HOME_SCREEN_LABEL = "Home Screen";
const STAY_LABEL = "Stay here";

// Labels that reset to the home/landing screen (handled client-side, never sent).
const HOME_LABELS = new Set([HOME_LABEL, MAIN_SCREEN_LABEL, HOME_SCREEN_LABEL]);

// Typed messages that signal the user wants to leave — intercepted to offer the main screen.
const EXIT_MESSAGES = new Set(["exit", "quit", "close", "cancel", "bye", "goodbye", "leave", "log out", "logout"]);

// Clickable quick-reply chips shown in the chat, keyed by the current workflow step.
const SUGGESTIONS: Record<string, string[]> = {
  greeting: ["I want to buy products", HOME_SCREEN_LABEL],
  confirmed: ["Place another order", "View order details", HOME_SCREEN_LABEL],
};

// Chips shown when an exit is requested, offering to return to the main screen or stay.
const EXIT_SUGGESTIONS = [MAIN_SCREEN_LABEL, STAY_LABEL];

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
  const [exiting, setExiting] = useState(false);
  // Server-driven chips for the current proposal turn (empty for ordering turns).
  const [serverSuggestions, setServerSuggestions] = useState<Suggestion[]>([]);
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
    setExiting(false);
    setServerSuggestions([]);
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

    // Exit intent: don't post to the backend — offer to return to the main screen.
    if (!silent && EXIT_MESSAGES.has(lower)) {
      setMessages((prev) => [
        ...prev,
        { role: "user", text: message },
        { role: "assistant", text: "Would you like to go back to the main screen?" },
      ]);
      setExiting(true);
      return;
    }
    setExiting(false);
    setServerSuggestions([]); // cleared now; repopulated by the turn's done event

    if (RESET_MESSAGES.has(lower)) setCartCount(0);
    if (MENU_KEY_BY_MESSAGE.has(lower)) setActiveMenu(MENU_KEY_BY_MESSAGE.get(lower)!);

    setSending(true);
    if (!silent) {
      setMessages((prev) => [...prev, { role: "user", text: message }, { role: "assistant", text: "" }]);
    }

    let assistantText = "";
    const incomingUi: UIPayload[] = [];

    const setAssistant = (text: string, html = false) => {
      if (silent) return;
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", text, html };
        return next;
      });
    };

    try {
      await sendMessage(
        conversationId,
        message,
        payload,
        {
          onText: (chunk) => {
            assistantText += chunk;
            setAssistant(assistantText);
          },
          onUi: (p) => {
            incomingUi.push(p);
            if (p.component === "Cart") setCartCount((p.data as CartData).item_count);
          },
          onDone: ({ step: turnStep, mode, suggestions }) => {
            if (incomingUi.length) setPanel(incomingUi);
            setStep(turnStep);
            setServerSuggestions(suggestions);
            // Proposal answers carry light HTML; re-render the bubble as rich text.
            if (mode === "proposal") setAssistant(assistantText, true);
          },
        },
        { intent: opts.intent ?? null },
      );
    } catch {
      setAssistant("Sorry, something went wrong talking to the assistant.");
    } finally {
      setSending(false);
    }
  }

  const started = messages.length > 0;

  // Local label-only chips (exit + step-based) route through here; server-driven
  // proposal chips post their message (and topic intent) directly.
  function onLabelChip(s: string) {
    if (HOME_LABELS.has(s)) resetToHome();
    else if (s === STAY_LABEL) setExiting(false);
    else send(s);
  }

  // Chip precedence: an exit prompt > a proposal turn's chips > step-based defaults.
  const chips: Chip[] = exiting
    ? EXIT_SUGGESTIONS.map((s) => ({ label: s, onClick: () => onLabelChip(s) }))
    : serverSuggestions.length
      ? serverSuggestions.map((s) => ({
          label: s.label,
          onClick: () =>
            HOME_LABELS.has(s.label)
              ? resetToHome()
              : send(s.message, null, s.intent ? { intent: s.intent } : {}),
        }))
      : (started ? SUGGESTIONS[step] ?? [] : []).map((s) => ({ label: s, onClick: () => onLabelChip(s) }));

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
          onNewChat={resetToHome}
        />
        {error && <div className="bg-red-50 text-red-700 text-sm px-6 py-2">{error}</div>}

        {!started ? (
          <Landing onSend={send} disabled={sending || !conversationId} />
        ) : (
          <div className="flex-1 min-h-0 flex">
            <section
              className={`flex flex-col min-h-0 ${
                panel.length > 0 ? "w-1/2 border-r border-gray-200" : "flex-1"
              }`}
            >
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-3">
                {messages.map((m, i) => (
                  <MessageBubble key={i} role={m.role} text={m.text} html={m.html} />
                ))}
              </div>
              {chips.length > 0 && (
                <div className="px-6 pb-2 flex flex-wrap gap-2">
                  {chips.map((c, i) => (
                    <button
                      key={`${c.label}-${i}`}
                      onClick={c.onClick}
                      disabled={sending}
                      className="border border-schaeffler-green text-schaeffler-green text-sm rounded-full px-3 py-1 hover:bg-schaeffler-greenLight disabled:opacity-40"
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              )}
              <ChatInput onSend={send} disabled={sending} />
            </section>

            {panel.length > 0 && (
              <section className="w-1/2 overflow-y-auto p-6 bg-gray-50">
                <div className="space-y-4">
                  {panel.map((p, i) => (
                    <div key={i}>{renderWidget(p, send)}</div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ role, text, html }: ChatMessage) {
  const isUser = role === "user";
  const className = `max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
    isUser ? "bg-schaeffler-green text-white" : "bg-white border border-gray-200 text-gray-800"
  }`;
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Proposal answers are trusted, server-controlled content (app/proposal/flows.py),
          so light HTML (e.g. <strong>) is rendered rather than escaped. */}
      {html ? (
        <div className={className} dangerouslySetInnerHTML={{ __html: text }} />
      ) : (
        <div className={className}>{text || (isUser ? "" : "…")}</div>
      )}
    </div>
  );
}
