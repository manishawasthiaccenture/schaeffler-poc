import type { WidgetProps } from "./widget";
import type { ProductDetailsData } from "../types/contract";
import { CheckIcon } from "../shell/icons";

export function ProductDetails({ data, send }: WidgetProps<ProductDetailsData>) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800">{data.sku}</h2>
      <p className="text-sm text-gray-500">{data.description}</p>
      <p className="text-xs text-gray-400 mt-1">{data.category}</p>

      <div className="mt-4 flex items-center gap-2 text-sm">
        {data.in_stock ? (
          <span className="inline-flex items-center gap-1 text-schaeffler-green">
            <CheckIcon className="w-4 h-4" /> In stock
          </span>
        ) : (
          <span className="text-amber-600">Out of stock</span>
        )}
        <span className="text-gray-400">· lead time {data.lead_time_days} days</span>
      </div>

      {Object.keys(data.attributes).length > 0 && (
        <div className="mt-4">
          <div className="text-xs uppercase tracking-wide text-gray-400 pb-1">Specifications</div>
          {Object.entries(data.attributes).map(([key, value]) => (
            <div key={key} className="flex justify-between py-1 text-sm border-t border-gray-50">
              <span className="text-gray-500 capitalize">{key.replace(/_/g, " ")}</span>
              <span className="text-gray-800">{String(value)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4">
        <div className="text-xs uppercase tracking-wide text-gray-400 pb-1">Price tiers</div>
        {data.price_tiers.map((tier, i) => (
          <div key={i} className="flex justify-between py-1 text-sm border-t border-gray-50">
            <span className="text-gray-600">Qty {tier.range}</span>
            <span className="text-gray-800">{tier.unit_price_display}</span>
          </div>
        ))}
      </div>

      <p className="text-sm text-gray-600 mt-4">Would you like to add this to your cart?</p>
      <div className="flex gap-3 mt-2">
        <button
          onClick={() => send("add to cart", { sku: data.sku, qty: 1 })}
          className="flex-1 bg-schaeffler-green text-white rounded-full py-2 hover:bg-schaeffler-greenDark"
        >
          Add to cart
        </button>
        <button
          onClick={() => send("show cart", null, { silent: true })}
          className="flex-1 border border-gray-300 text-gray-700 rounded-full py-2 hover:bg-gray-50"
        >
          Not now
        </button>
      </div>
    </div>
  );
}
