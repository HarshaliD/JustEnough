import React, { useEffect, useState, useRef } from 'react';

/**
 * CursorEffects provides:
 * 1. Ambient cursor-following spotlight on the canvas for dynamic depth.
 * 2. Expanding water-drop ripple shockwave on every mouse click.
 */
export default function CursorEffects() {
  const [ripples, setRipples] = useState([]);
  const spotlightRef = useRef(null);
  const posRef = useRef({ x: -1000, y: -1000 });
  const isVisibleRef = useRef(false);

  useEffect(() => {
    let animFrameId;

    const handlePointerMove = (e) => {
      posRef.current = { x: e.clientX, y: e.clientY };
      if (!isVisibleRef.current) {
        isVisibleRef.current = true;
        if (spotlightRef.current) {
          spotlightRef.current.style.opacity = '1';
        }
      }
    };

    const handleMouseLeave = () => {
      isVisibleRef.current = false;
      if (spotlightRef.current) {
        spotlightRef.current.style.opacity = '0';
      }
    };

    const updateSpotlight = () => {
      if (spotlightRef.current && isVisibleRef.current) {
        const { x, y } = posRef.current;
        spotlightRef.current.style.background = `radial-gradient(600px circle at ${x}px ${y}px, rgba(37, 99, 235, 0.08) 0%, rgba(79, 70, 229, 0.04) 35%, transparent 70%)`;
      }
      animFrameId = requestAnimationFrame(updateSpotlight);
    };

    const handlePointerDown = (e) => {
      // Don't spawn ripples on right-clicks
      if (e.button !== 0) return;

      const newRipple = {
        id: `${Date.now()}-${Math.random()}`,
        x: e.clientX,
        y: e.clientY,
      };

      setRipples((prev) => [...prev.slice(-12), newRipple]);

      // Remove after animation completes
      setTimeout(() => {
        setRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
      }, 600);
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('pointerdown', handlePointerDown, { passive: true });
    animFrameId = requestAnimationFrame(updateSpotlight);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('pointerdown', handlePointerDown);
      cancelAnimationFrame(animFrameId);
    };
  }, []);

  return (
    <>
      {/* Ambient cursor spotlight */}
      <div
        ref={spotlightRef}
        className="pointer-events-none fixed inset-0 z-30 transition-opacity duration-300"
        style={{ opacity: 0 }}
        aria-hidden="true"
      />

      {/* Click ripple shockwaves */}
      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          className="click-ripple"
          style={{
            left: `${ripple.x}px`,
            top: `${ripple.y}px`,
            width: '90px',
            height: '90px',
          }}
          aria-hidden="true"
        />
      ))}
    </>
  );
}
