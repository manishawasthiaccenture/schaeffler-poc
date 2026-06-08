import type { WidgetProps } from "./widget";
import type { StubMessageData } from "../types/contract";

export function StubMessage({ data }: WidgetProps<StubMessageData>) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-800">{data.title}</h2>
      <p className="text-sm text-gray-500 mt-1">{data.message}</p>
    </div>
  );
}
