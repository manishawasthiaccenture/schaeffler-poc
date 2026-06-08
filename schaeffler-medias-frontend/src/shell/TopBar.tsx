import { RobotIcon, CloseIcon } from "./icons";

interface Props {
  onClose?: () => void;
}

export function TopBar({ onClose }: Props) {
  return (
    <div className="bg-schaeffler-green text-white flex items-center justify-between px-5 py-3">
      <div className="flex items-center gap-2">
        <RobotIcon className="w-5 h-5" />
        <span className="font-medium">Ask me anything…</span>
      </div>
      <button aria-label="Close" onClick={onClose} className="text-white/90 hover:text-white">
        <CloseIcon className="w-5 h-5" />
      </button>
    </div>
  );
}
