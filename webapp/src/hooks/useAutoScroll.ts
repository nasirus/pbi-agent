import { useCallback, useEffect, useRef, useState } from "react";

const SCROLL_THRESHOLD = 80;
const PROGRAMMATIC_SCROLL_RESET_MS = 120;

export function useAutoScroll(
  changeKey: unknown,
  options?: {
    followOnChange?: boolean;
  },
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [showNewMessages, setShowNewMessages] = useState(false);
  const userScrolledRef = useRef(false);
  const rafRef = useRef<number>(0);
  const programmaticScrollTimeoutRef = useRef<number>(0);
  const programmaticScrollRef = useRef(false);
  const followOnChange = options?.followOnChange ?? true;

  const markProgrammaticScroll = useCallback(() => {
    programmaticScrollRef.current = true;
    window.clearTimeout(programmaticScrollTimeoutRef.current);
    programmaticScrollTimeoutRef.current = window.setTimeout(() => {
      programmaticScrollRef.current = false;
    }, PROGRAMMATIC_SCROLL_RESET_MS);
  }, []);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD;
    if (programmaticScrollRef.current) {
      if (atBottom) {
        setShowNewMessages(false);
      }
      return;
    }
    userScrolledRef.current = !atBottom;
    if (atBottom) {
      setShowNewMessages(false);
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!followOnChange) return;
    if (!userScrolledRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        markProgrammaticScroll();
        el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
      });
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- badge visibility should change with the message batch that triggered this effect, not one frame later.
      setShowNewMessages(true);
    }
  }, [changeKey, followOnChange, markProgrammaticScroll]);

  useEffect(() => {
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.clearTimeout(programmaticScrollTimeoutRef.current);
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    markProgrammaticScroll();
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    userScrolledRef.current = false;
    setShowNewMessages(false);
  }, [markProgrammaticScroll]);

  return {
    containerRef,
    showNewMessages,
    setShowNewMessages,
    scrollToBottom,
    userScrolledRef,
    markProgrammaticScroll,
  };
}
