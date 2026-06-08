import type { FC } from "react";
import type { UIPayload } from "../types/contract";
import type { SendFn, WidgetProps } from "./widget";
import { UploadWidget } from "./UploadWidget";
import { TypePrompt } from "./TypePrompt";
import { MappingTable } from "./MappingTable";
import { QuoteCard } from "./QuoteCard";
import { Cart } from "./Cart";
import { CheckoutForm } from "./CheckoutForm";
import { Confirmation } from "./Confirmation";
import { ProductDetails } from "./ProductDetails";
import { StubMessage } from "./StubMessage";

// component name (from the backend §10 payload) -> React widget.
const registry: Record<string, FC<WidgetProps<never>>> = {
  UploadWidget,
  TypePrompt,
  MappingTable,
  QuoteCard,
  Cart,
  CheckoutForm,
  Confirmation,
  ProductDetails,
  StubMessage,
};

export function renderWidget(payload: UIPayload, send: SendFn) {
  const Widget = registry[payload.component];
  if (!Widget) {
    return <div className="text-sm text-gray-400">Unknown component: {payload.component}</div>;
  }
  return <Widget data={payload.data as never} send={send} />;
}
