import type { WidgetProps } from "./widget";
import type { EquivalentPromptData } from "../types/contract";

export function EquivalentPrompt({ data, send }: WidgetProps<EquivalentPromptData>) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800">No direct Schaeffler product</h2>
      <p className="text-sm text-gray-600 mt-2">
        <span className="font-medium">{data.raw}</span> isn't a Schaeffler designation. The closest
        Schaeffler equivalent is <span className="font-medium">{data.sku}</span> — {data.description}.
      </p>
      <p className="text-sm text-gray-600 mt-3">Would you like to see its product details?</p>
      <div className="flex gap-3 mt-3">
        <button
          onClick={() => send(`show details for ${data.sku}`, { sku: data.sku })}
          className="flex-1 bg-schaeffler-green text-white rounded-full py-2 hover:bg-schaeffler-greenDark"
        >
          Show details
        </button>
        <button
          onClick={() => send("show cart", null, { silent: true })}
          className="flex-1 border border-gray-300 text-gray-700 rounded-full py-2 hover:bg-gray-50"
        >
          No, thanks
        </button>
      </div>
    </div>
  );
}
