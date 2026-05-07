import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import clsx from "clsx";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  size?: "md" | "lg" | "xl" | "xxl";
  children: React.ReactNode;
}

const sizeClass = {
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
  xxl: "max-w-6xl",
};

export default function Modal({ isOpen, onClose, title, size = "lg", children }: Props) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={clsx(
          "relative w-full bg-bg-panel border border-border rounded-lg shadow-2xl flex flex-col overflow-hidden",
          sizeClass[size],
          "max-h-[90vh]",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0">
          <h2 className="text-sm font-semibold text-text-bright">{title}</h2>
          <button
            className="text-text-dim hover:text-text transition-colors"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
        {/* Body — scrollable */}
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
