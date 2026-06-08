// Minimal inline SVG icons (stroke = currentColor) used across the shell and widgets.
interface IconProps {
  className?: string;
}

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const RobotIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <rect x="4" y="8" width="16" height="12" rx="2" />
    <path d="M12 8V4M8 4h8" />
    <circle cx="9" cy="14" r="1" />
    <circle cx="15" cy="14" r="1" />
  </svg>
);

export const CloseIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

export const MenuIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

export const ComposeIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
  </svg>
);

export const MicIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </svg>
);

export const AttachIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M21 11.5 12 20a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-3-3l8-8" />
  </svg>
);

export const SendIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M22 2 11 13M22 2l-7 20-4-9-9-4Z" />
  </svg>
);

export const DocIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <path d="M14 2v6h6" />
  </svg>
);

export const CartIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <circle cx="9" cy="21" r="1" />
    <circle cx="20" cy="21" r="1" />
    <path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" />
  </svg>
);

export const HelpIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <circle cx="12" cy="12" r="10" />
    <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4" />
    <circle cx="12" cy="17" r="0.5" />
  </svg>
);

export const WrenchIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M14.7 6.3a4 4 0 0 0 5 5l-9 9-5-5 9-9Z" />
  </svg>
);

export const ShuffleIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
  </svg>
);

export const PackageIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M21 8 12 3 3 8l9 5 9-5Z" />
    <path d="M3 8v8l9 5 9-5V8" />
  </svg>
);

export const CheckIcon = ({ className }: IconProps) => (
  <svg className={className} {...base}>
    <path d="M20 6 9 17l-5-5" />
  </svg>
);
