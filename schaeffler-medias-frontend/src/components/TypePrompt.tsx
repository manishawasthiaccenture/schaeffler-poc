import type { WidgetProps } from "./widget";
import type { TypePromptData } from "../types/contract";

export function TypePrompt({ data }: WidgetProps<TypePromptData>) {
  return (
    <div className="bg-schaeffler-greenLight rounded-lg p-4 text-sm text-gray-700">
      Type your product list in the chat — one product per line with quantities.
      <div className="text-gray-500 mt-1">e.g. {data.placeholder}</div>
    </div>
  );
}
