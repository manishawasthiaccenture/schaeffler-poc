import { useState } from "react";
import type { WidgetProps } from "./widget";
import type { AlreadyInCartData } from "../types/contract";

export function AlreadyInCart({ data, send }: WidgetProps<AlreadyInCartData>) {
  const [qty, setQty] = useState(1);
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800">Already in your cart</h2>
      <p className="text-sm text-gray-600 mt-2">
        <span className="font-medium">{data.sku}</span> is already in your cart (quantity{" "}
        {data.current_qty}). Would you like to add it again?
      </p>
      <div className="flex items-center gap-3 mt-4">
        <span className="text-sm text-gray-500">Quantity to add</span>
        <div className="flex items-center border border-gray-300 rounded-full">
          <button
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            className="px-3 py-1 text-gray-600 hover:text-gray-900"
            aria-label="Decrease quantity"
          >
            −
          </button>
          <span className="px-3 text-sm tabular-nums">{qty}</span>
          <button
            onClick={() => setQty((q) => q + 1)}
            className="px-3 py-1 text-gray-600 hover:text-gray-900"
            aria-label="Increase quantity"
          >
            +
          </button>
        </div>
      </div>
      <div className="flex gap-3 mt-4">
        <button
          onClick={() => send("add to cart", { sku: data.sku, qty, confirm_add: true })}
          className="flex-1 bg-schaeffler-green text-white rounded-full py-2 hover:bg-schaeffler-greenDark"
        >
          Add {qty} more
        </button>
        <button
          onClick={() => send("show cart", null, { silent: true })}
          className="flex-1 border border-gray-300 text-gray-700 rounded-full py-2 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
