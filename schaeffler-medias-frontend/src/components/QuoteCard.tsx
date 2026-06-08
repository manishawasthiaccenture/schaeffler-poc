import type { WidgetProps } from "./widget";
import type { QuoteCardData } from "../types/contract";
import { quotePdfUrl } from "../api/client";
import { DocIcon } from "../shell/icons";

export function QuoteCard({ data, send }: WidgetProps<QuoteCardData>) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            Quote {data.quote_id}
            <span className="bg-schaeffler-greenLight text-schaeffler-green text-xs px-2 py-0.5 rounded-full">
              {data.status}
            </span>
          </div>
          <DocIcon className="w-5 h-5 text-gray-400" />
        </div>

        <div className="text-3xl font-semibold text-gray-800 mt-2">{data.total_display}</div>
        <p className="text-sm text-gray-400">Available until {data.valid_until}</p>

        <a
          href={quotePdfUrl(data.quote_id)}
          target="_blank"
          rel="noreferrer"
          className="block text-center bg-schaeffler-green text-white rounded-full py-2 mt-4 hover:bg-schaeffler-greenDark"
        >
          Download quote
        </a>
        <button
          onClick={() => send("Proceed to checkout")}
          className="w-full border border-gray-300 text-gray-700 rounded-full py-2 mt-2 hover:bg-gray-50"
        >
          Proceed to checkout
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="font-medium text-gray-800">Products in this quote</h3>
        <div className="mt-3 space-y-2">
          {data.lines.map((line, i) => (
            <div key={i} className="flex justify-between items-center bg-gray-50 rounded px-3 py-2 text-sm">
              <span className="text-gray-700">
                {line.sku}
                <span className="block text-gray-400">Qty: {line.qty}</span>
                <button
                  onClick={() => send(`details for ${line.sku}`)}
                  className="text-schaeffler-green text-xs hover:underline"
                >
                  View details
                </button>
              </span>
              <span className="text-gray-600">{line.line_total_display}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
