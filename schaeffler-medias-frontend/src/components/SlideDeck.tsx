import { useEffect, useState } from "react";
import type { WidgetProps } from "./widget";
import type { SlideDeckData, SlideData } from "../types/contract";
import { slideUrl } from "../api/client";

// Proposal slides for an RFQ topic, shown as a 3D cover-flow: the active slide faces
// front while neighbours angle back to either side. Auto-advances; side slides,
// chevrons and dots all navigate. A single slide just renders flat. A missing image
// (404) falls back to a labelled placeholder.
export function SlideDeck({ data }: WidgetProps<SlideDeckData>) {
  const slides = data.slides ?? [];
  const [idx, setIdx] = useState(0);
  const key = slides.map((s) => s.image).join("|");

  // Reset to the first slide whenever the set of slides changes (new answer).
  useEffect(() => setIdx(0), [key]);

  // Auto-advance the cover-flow.
  useEffect(() => {
    if (slides.length < 2) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % slides.length), 4500);
    return () => clearInterval(t);
  }, [key, slides.length]);

  if (!slides.length) return null;

  if (slides.length === 1) {
    return (
      <div className="rounded-lg border border-gray-200 shadow-sm bg-white overflow-hidden">
        <Slide slide={slides[0]} flat />
      </div>
    );
  }

  const go = (i: number) => setIdx((i + slides.length) % slides.length);

  return (
    <div>
      <div
        className="relative aspect-video overflow-hidden rounded-lg"
        style={{ perspective: "1200px" }}
      >
        <div className="absolute inset-0" style={{ transformStyle: "preserve-3d" }}>
          {slides.map((s, i) => {
            const offset = i - idx;
            const abs = Math.abs(offset);
            const active = offset === 0;
            // Center each card (translate -50%,-50%), then fan neighbours out in 3D.
            const transform =
              `translate(-50%, -50%) translateX(${offset * 52}%) ` +
              `translateZ(${active ? 0 : -160}px) ` +
              `rotateY(${active ? 0 : offset < 0 ? 42 : -42}deg) ` +
              `scale(${active ? 1 : 0.82})`;
            return (
              <div
                key={s.image}
                onClick={() => !active && go(i)}
                aria-hidden={!active}
                className="absolute top-1/2 left-1/2 w-[93%] aspect-video transition-all duration-500 ease-out"
                style={{
                  transform,
                  zIndex: 100 - abs,
                  opacity: abs > 2 ? 0 : 1,
                  pointerEvents: abs > 2 ? "none" : "auto",
                  cursor: active ? "default" : "pointer",
                  filter: active ? "none" : "brightness(0.7)",
                }}
              >
                <Slide slide={s} />
              </div>
            );
          })}
        </div>
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

// `flat` renders the natural-aspect image (single-slide case); otherwise the slide
// fills its cover-flow card.
function Slide({ slide, flat = false }: { slide: SlideData; flat?: boolean }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        className={`flex flex-col items-center justify-center bg-gray-50 text-center p-8 ${
          flat ? "aspect-video" : "w-full h-full rounded-lg border border-gray-200"
        }`}
      >
        <p className="text-sm text-gray-500">{slide.label}</p>
        <p className="text-xs text-gray-400 mt-1">Slide image not available</p>
      </div>
    );
  }
  if (flat) {
    return (
      <img
        src={slideUrl(slide.image)}
        alt={slide.label}
        loading="lazy"
        className="block w-full h-auto"
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div className="w-full h-full rounded-lg overflow-hidden border border-gray-200 shadow-xl bg-white">
      <img
        src={slideUrl(slide.image)}
        alt={slide.label}
        loading="lazy"
        className="w-full h-full object-contain"
        onError={() => setFailed(true)}
      />
    </div>
  );
}

function NavButton({ side, onClick }: { side: "left" | "right"; onClick: () => void }) {
  return (
    <button
      aria-label={side === "left" ? "Previous slide" : "Next slide"}
      onClick={onClick}
      className={`absolute top-1/2 -translate-y-1/2 z-[200] ${side === "left" ? "left-2" : "right-2"}
        w-8 h-8 rounded-full bg-white/80 hover:bg-white shadow flex items-center justify-center
        text-gray-700 transition`}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="w-4 h-4">
        {side === "left" ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 6l6 6-6 6" />}
      </svg>
    </button>
  );
}
