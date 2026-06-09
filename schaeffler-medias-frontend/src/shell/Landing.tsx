import { useState } from "react";
import { SendIcon, MicIcon, AttachIcon } from "./icons";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

// Clean default screen: the medias header and a single chat box. Ordering options
// and proposal results only appear once the user asks (in the chat thread / side
// panel) — nothing is pre-fed here.
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
    <div className="flex-1 overflow-y-auto px-8 py-10 flex flex-col justify-center">
      <div className="max-w-3xl w-full mx-auto">
        <h1 className="text-center text-4xl font-semibold text-gray-800">medias</h1>
        <p className="mt-3 text-center text-gray-600">
          Hi, I'm your <span className="font-semibold text-gray-800">Medias Co-Driver</span>. How can I
          help — order or proposal question?
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
      </div>
    </div>
  );
}
