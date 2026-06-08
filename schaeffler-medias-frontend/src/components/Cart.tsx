import type { WidgetProps } from "./widget";
import type { CartData } from "../types/contract";
import { CartIcon } from "../shell/icons";

export function Cart({ data, send }: WidgetProps<CartData>) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center gap-2 font-semibold text-gray-800">
        <CartIcon className="w-5 h-5" />
        Shopping Cart
        <span className="text-gray-400 font-normal text-sm">({data.item_count} items)</span>
      </div>

      {data.items.length === 0 ? (
        <p className="text-sm text-gray-400 mt-4">Your cart is empty.</p>
      ) : (
        <div className="mt-4 border-t border-gray-100">
          {data.items.map((item, i) => (
            <div key={i} className="flex justify-between gap-4 py-3 border-t border-gray-50 first:border-t-0">
              <div className="text-sm">
                <div className="font-medium text-gray-800">{item.sku}</div>
                <div className="text-gray-400">{item.description}</div>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    aria-label="Decrease quantity"
                    onClick={() =>
                      send("update cart", { sku: item.sku, qty: Math.max(1, item.qty - 1) }, { silent: true })
                    }
                    className="w-6 h-6 rounded border border-gray-300 text-gray-600 hover:border-schaeffler-green leading-none"
                  >
                    −
                  </button>
                  <span className="w-8 text-center">{item.qty}</span>
                  <button
                    aria-label="Increase quantity"
                    onClick={() =>
                      send("update cart", { sku: item.sku, qty: item.qty + 1 }, { silent: true })
                    }
                    className="w-6 h-6 rounded border border-gray-300 text-gray-600 hover:border-schaeffler-green leading-none"
                  >
                    +
                  </button>
                  <span className="text-gray-400 text-xs">× {item.unit_price_display}</span>
                </div>
                <div className="flex gap-3 mt-1">
                  <button
                    onClick={() => send(`details for ${item.sku}`)}
                    className="text-schaeffler-green text-xs hover:underline"
                  >
                    View details
                  </button>
                  <button
                    onClick={() => send("remove item", { sku: item.sku }, { silent: true })}
                    className="text-red-500 text-xs hover:underline"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <div className="font-medium text-gray-800 whitespace-nowrap">{item.line_total_display}</div>
            </div>
          ))}
        </div>
      )}

      {data.items.length > 0 && (
        <>
          <div className="flex justify-between font-semibold text-gray-800 mt-3 pt-3 border-t border-gray-100">
            <span>Total</span>
            <span>{data.total_display}</span>
          </div>
          <button
            onClick={() => send("Proceed to checkout")}
            className="w-full bg-schaeffler-green text-white rounded-full py-2 mt-4 hover:bg-schaeffler-greenDark"
          >
            Proceed to checkout
          </button>
        </>
      )}
    </div>
  );
}
