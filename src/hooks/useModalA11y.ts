import { useEffect, useRef } from 'react';

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * Dialog semantics + keyboard behaviour for an overlay that already exists.
 *
 * Fifteen overlays shipped with no role="dialog", no aria-modal, no Escape
 * handler and no focus containment: a keyboard user could not dismiss any of
 * them, focus walked the page behind the scrim, and a screen reader announced
 * nothing. Two of them also closed on a click that a touch-only user can never
 * perform.
 *
 * A <Modal> shell would have meant rewriting 15 headers, 15 footers and their
 * sticky/scroll behaviour. This fixes the actual defects in three lines per
 * call site and changes no layout.
 *
 * Usage:
 *   const ref = useModalA11y<HTMLDivElement>(isOpen, onClose);
 *   <div ref={ref} role="dialog" aria-modal="true" aria-label="..." tabIndex={-1}>
 */
export function useModalA11y<T extends HTMLElement = HTMLDivElement>(
  isOpen: boolean,
  onClose?: () => void,
) {
  const ref = useRef<T>(null);

  // Held in a ref so the effect does not depend on the callback identity.
  // Most call sites pass an inline arrow, which changes on every parent
  // render; with onClose in the deps the effect would re-run and yank focus
  // back to the first field mid-interaction.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;
    const node = ref.current;
    if (!node) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    const focusables = () =>
      Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement
      );

    // Land focus inside the dialog. Without this, Tab continues from wherever
    // the opener was, which is behind the scrim.
    const initial = focusables()[0];
    (initial ?? node).focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Capture phase, so page-level Escape handlers (e.g. the presentation
        // mode toggle in ChatDashboardPage) do not also fire behind the modal.
        e.preventDefault();
        e.stopPropagation();
        closeRef.current?.();
        return;
      }
      if (e.key !== 'Tab') return;

      const list = focusables();
      if (list.length === 0) {
        e.preventDefault();
        node.focus();
        return;
      }
      const first = list[0];
      const last = list[list.length - 1];
      const active = document.activeElement;

      if (e.shiftKey && (active === first || active === node)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || active === node)) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown, true);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown, true);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [isOpen]);

  return ref;
}