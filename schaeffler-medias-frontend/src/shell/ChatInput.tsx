import { useState } from "react";
import { SendIcon, MicIcon, AttachIcon } from "./icons";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  function submit() {
    const value = text.trim();
    if (value) {
      onSend(value);
      setText("");
    }
  }

  return (
    <div className="border-t border-gray-200 p-4">
      <div className="flex items-end gap-3 border border-gray-300 rounded-2xl px-4 py-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
          disabled={disabled}
          placeholder="Ask medias…  (Shift+Enter for a new line)"
          className="flex-1 resize-none outline-none text-sm bg-transparent max-h-32 disabled:opacity-50"
        />
        <MicIcon className="w-5 h-5 text-gray-300 shrink-0" />
        <AttachIcon className="w-5 h-5 text-gray-300 shrink-0" />
        <button
          onClick={submit}
          disabled={disabled}
          aria-label="Send"
          className="text-schaeffler-green disabled:opacity-40 shrink-0"
        >
          <SendIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
