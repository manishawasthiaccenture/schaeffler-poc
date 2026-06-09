import { useEffect, useState } from "react";
import type { WidgetProps } from "./widget";
import type { SlideDeckData, SlideData } from "../types/contract";
import { slideUrl } from "../api/client";

// Proposal slides for an RFQ topic, shown with a Ken Burns effect: each slide slowly
// zooms and pans while displayed. A single slide just animates; multiple slides
// crossfade from one Ken Burns shot to the next, auto-advancing, with prev/next + dots.
// A missing image (404) falls back to a labelled placeholder.
export function SlideDeck({ data }: WidgetProps<SlideDeckData>) {
  const slides = data.slides ?? [];
  const [idx, setIdx] = useState(0);
  const key = slides.map((s) => s.image).join("|");

  // Reset to the first slide whenever the set of slides changes (new answer).
  useEffect(() => setIdx(0), [key]);

  // Auto-advance through the slides.
  useEffect(() => {
    if (slides.length < 2) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % slides.length), 5000);
    return () => clearInterval(t);
  }, [key, slides.length]);

  if (!slides.length) return null;

  if (slides.length === 1) {
    return (
      <div className="relative aspect-video overflow-hidden rounded-lg border border-gray-200 shadow-sm bg-white">
        <Slide slide={slides[0]} variant={0} />
      </div>
    );
  }

  const go = (i: number) => setIdx((i + slides.length) % slides.length);

  return (
    <div>
      <div className="relative aspect-video overflow-hidden rounded-lg border border-gray-200 shadow-sm bg-white">
        {slides.map((s, i) => (
          <div
            key={s.image}
            aria-hidden={i !== idx}
            className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
              i === idx ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"
            }`}
          >
            <Slide slide={s} variant={i} />
          </div>
        ))}
        <NavButton side="left" onClick={() => go(idx - 1)} />
        <NavButton side="right" onClick={() => go(idx + 1)} />
      </div>

      <div className="mt-2 flex justify-center gap-1.5">
        {slides.map((s, i) => (
          <button
            key={s.image}
            aria-label={`Go to slide ${i + 1}`}
            onClick={() => setIdx(i)}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === idx ? "w-5 bg-schaeffler-green" : "w-1.5 bg-gray-300 hover:bg-gray-400"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

function Slide({ slide, variant }: { slide: SlideData; variant: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 text-center p-8">
        <p className="text-sm text-gray-500">{slide.label}</p>
        <p className="text-xs text-gray-400 mt-1">Slide image not available</p>
      </div>
    );
  }
  // Alternate the Ken Burns direction per slide so a crossfade stays dynamic.
  const kb = variant % 2 === 0 ? "ken-burns-a" : "ken-burns-b";
  return (
    <img
      src={slideUrl(slide.image)}
      alt={slide.label}
      loading="lazy"
      className={`w-full h-full object-cover ${kb}`}
      onError={() => setFailed(true)}
    />
  );
}

function NavButton({ side, onClick }: { side: "left" | "right"; onClick: () => void }) {
  return (
    <button
      aria-label={side === "left" ? "Previous slide" : "Next slide"}
      onClick={onClick}
      className={`absolute top-1/2 -translate-y-1/2 z-20 ${side === "left" ? "left-2" : "right-2"}
        w-8 h-8 rounded-full bg-white/80 hover:bg-white shadow flex items-center justify-center
        text-gray-700 transition`}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="w-4 h-4">
        {side === "left" ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 6l6 6-6 6" />}
      </svg>
    </button>
  );
}
