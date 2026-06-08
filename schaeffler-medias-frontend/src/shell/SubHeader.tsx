import { useState } from "react";
import { MenuIcon, ComposeIcon, CartIcon } from "./icons";

export interface MenuItem {
  key: string;
  label: string;
  message: string;
}

interface Props {
  menu?: MenuItem[];
  activeMenu?: string;
  onSelectMenu?: (item: MenuItem) => void;
  cartCount?: number;
  onShowCart?: () => void;
}

export function SubHeader({ menu = [], activeMenu, onSelectMenu, cartCount = 0, onShowCart }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative flex items-center justify-between px-5 py-3 border-b border-gray-200">
      <div className="flex items-center gap-4 text-gray-600">
        <button aria-label="Menu" className="hover:text-gray-900" onClick={() => setOpen((o) => !o)}>
          <MenuIcon className="w-5 h-5" />
        </button>
        <button aria-label="New chat" className="hover:text-gray-900">
          <ComposeIcon className="w-5 h-5" />
        </button>
      </div>

      {open && menu.length > 0 && (
        <div className="absolute left-4 top-14 z-10 w-60 bg-white border border-gray-200 rounded-lg shadow-lg py-1">
          {menu.map((item) => (
            <button
              key={item.key}
              onClick={() => {
                onSelectMenu?.(item);
                setOpen(false);
              }}
              className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                item.key === activeMenu
                  ? "text-schaeffler-green font-medium bg-schaeffler-greenLight"
                  : "text-gray-700"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4">
        {cartCount > 0 && (
          <button
            aria-label="View cart"
            onClick={onShowCart}
            className="relative text-gray-600 hover:text-schaeffler-green"
          >
            <CartIcon className="w-5 h-5" />
            <span className="absolute -top-2 -right-2 bg-schaeffler-green text-white text-[10px] leading-none rounded-full px-1.5 py-0.5">
              {cartCount}
            </span>
          </button>
        )}
        <span className="font-bold tracking-wide text-schaeffler-green">SCHAEFFLER</span>
      </div>
    </div>
  );
}
