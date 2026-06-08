import type { WidgetProps } from "./widget";
import type { UploadWidgetData } from "../types/contract";
import { DocIcon } from "../shell/icons";

// Rendered but DISABLED in V1 (PRD D1) — storyboard-faithful, routes user to typed entry.
export function UploadWidget({ data }: WidgetProps<UploadWidgetData>) {
  return (
    <div className="bg-white rounded-lg border border-dashed border-gray-300 p-6 text-center opacity-70">
      <div className="mx-auto w-12 h-12 rounded bg-gray-100 flex items-center justify-center text-gray-400">
        <DocIcon className="w-6 h-6" />
      </div>
      <p className="text-sm text-gray-500 mt-3">{data.title}</p>
      <button
        disabled
        className="mt-3 bg-gray-300 text-white rounded-full px-4 py-2 text-sm cursor-not-allowed"
      >
        {data.button}
      </button>
      <p className="text-xs text-gray-400 mt-2">{data.note}</p>
    </div>
  );
}
