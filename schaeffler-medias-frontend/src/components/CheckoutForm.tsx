import { useState } from "react";
import type { WidgetProps } from "./widget";
import type { CheckoutFormData } from "../types/contract";
import { CheckIcon } from "../shell/icons";

export function CheckoutForm({ data, send }: WidgetProps<CheckoutFormData>) {
  const [po, setPo] = useState("");
  const [orderType, setOrderType] = useState("");
  const [comment, setComment] = useState("");

  const fields = data.fields;
  const canPlaceOrder = po.trim().length > 0; // FR-7: PO number required

  function placeOrder() {
    if (!canPlaceOrder) return;
    send("Place order", {
      purchase_order_number: po.trim(),
      order_type: orderType || null,
      comment: comment || null,
    });
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Checkout</h2>
        <button
          disabled={!canPlaceOrder}
          onClick={placeOrder}
          className="bg-schaeffler-green text-white text-sm rounded-full px-4 py-2 hover:bg-schaeffler-greenDark disabled:opacity-40"
        >
          Place order
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <label className="text-sm">
          <span className="block text-gray-600">
            {fields.purchase_order_number.label}
            {fields.purchase_order_number.required && "*"}
          </span>
          <input
            value={po}
            maxLength={fields.purchase_order_number.max_length}
            onChange={(e) => setPo(e.target.value)}
            className="mt-1 w-full border border-gray-300 rounded px-3 py-2 outline-none focus:border-schaeffler-green"
          />
          <span className="text-xs text-gray-400">
            max {fields.purchase_order_number.max_length} characters
          </span>
        </label>

        <label className="text-sm">
          <span className="block text-gray-600">{fields.order_type.label}</span>
          <select
            value={orderType}
            onChange={(e) => setOrderType(e.target.value)}
            className="mt-1 w-full border border-gray-300 rounded px-3 py-2 outline-none focus:border-schaeffler-green"
          >
            <option value="">—</option>
            {fields.order_type.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block text-sm mt-4">
        <span className="block text-gray-600">{fields.comment.label}</span>
        <textarea
          value={comment}
          maxLength={fields.comment.max_length}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          placeholder="Add a comment / order instruction"
          className="mt-1 w-full border border-gray-300 rounded px-3 py-2 outline-none focus:border-schaeffler-green"
        />
        <span className="text-xs text-gray-400">max {fields.comment.max_length} characters</span>
      </label>

      <p className="text-xs text-gray-400 mt-1">*mandatory</p>

      <div className="mt-4 border-t border-gray-100">
        {data.sections.map((section) => (
          <div
            key={section}
            className="flex items-center justify-between py-3 text-sm text-gray-700 border-t border-gray-50 first:border-t-0"
          >
            <span>{section}</span>
            <CheckIcon className="w-4 h-4 text-schaeffler-green" />
          </div>
        ))}
      </div>
    </div>
  );
}
