import type { WidgetProps } from "./widget";
import type { MappingTableData } from "../types/contract";
import { CheckIcon } from "../shell/icons";

export function MappingTable({ data, send }: WidgetProps<MappingTableData>) {
  const recognized = data.rows.filter((r) => r.status === "matched");
  const mapped = data.rows.filter((r) => r.status === "mapped");
  const missing = data.rows.filter((r) => r.status === "no_equivalent");
  const hasAcceptable = recognized.length > 0 || mapped.length > 0;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800">Product Review</h2>
      <p className="text-sm text-gray-500 mt-1">Confirm the products below to continue.</p>

      {recognized.length > 0 && (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Schaeffler products (recognized)</div>
          {recognized.map((row, i) => (
            <div key={i} className="flex items-center gap-2 py-2 text-sm border-t border-gray-50">
              <CheckIcon className="w-4 h-4 text-schaeffler-green shrink-0" />
              <span className="text-gray-800">{row.matched_sku}</span>
              <span className="text-gray-400">× {row.qty}</span>
            </div>
          ))}
        </div>
      )}

      {mapped.length > 0 && (
        <div className="mt-4">
          <div className="grid grid-cols-2 text-xs uppercase tracking-wide text-gray-400 pb-1">
            <span>Non-Schaeffler</span>
            <span>Schaeffler equivalent</span>
          </div>
          {mapped.map((row, i) => (
            <div key={i} className="grid grid-cols-2 items-center py-2 text-sm border-t border-gray-50">
              <span className="text-gray-700">
                {row.raw}
                <span className="text-gray-400"> × {row.qty}</span>
              </span>
              <span className="text-gray-800">{row.matched_sku}</span>
            </div>
          ))}
        </div>
      )}

      {missing.length > 0 && (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">No direct equivalent</div>
          {missing.map((row, i) => (
            <div key={i} className="py-2 text-sm border-t border-gray-50 text-gray-400 italic">
              {row.raw} — not found
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-3 mt-5">
        {hasAcceptable && (
          <button
            onClick={() => send("Accept all mappings and request a quote")}
            className="bg-schaeffler-green text-white text-sm rounded-full px-4 py-2 hover:bg-schaeffler-greenDark"
          >
            Accept all
          </button>
        )}
        <button
          onClick={() => send("Decline all and remove from list")}
          className="border border-red-500 text-red-600 text-sm rounded-full px-4 py-2 hover:bg-red-50"
        >
          Decline all and remove from list
        </button>
      </div>
    </div>
  );
}
