import type { WidgetProps } from "./widget";
import type { ConfirmationData } from "../types/contract";
import { PackageIcon, CheckIcon } from "../shell/icons";

export function Confirmation({ data }: WidgetProps<ConfirmationData>) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <div className="mx-auto w-16 h-16 rounded bg-gray-100 flex items-center justify-center text-gray-500">
        <PackageIcon className="w-8 h-8" />
      </div>
      <h2 className="mt-4 font-semibold text-gray-800">Thank you for your order!</h2>
      <p className="text-sm text-gray-500 mt-2">{data.message}</p>
      <div className="mt-4 inline-flex items-center gap-2 bg-schaeffler-greenLight text-schaeffler-green rounded px-4 py-2 text-sm">
        <CheckIcon className="w-4 h-4" />
        Order confirmed
      </div>
      <p className="text-xs text-gray-400 mt-2">Order {data.order_id}</p>
    </div>
  );
}
