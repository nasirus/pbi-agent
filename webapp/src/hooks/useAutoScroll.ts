import { useCallback, useEffect, useRef, useState } from "react";

const SCROLL_THRESHOLD = 80;

export function useAutoScroll(deps: unknown[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [showNewMessages, setShowNewMessages] = useState(false);
  const userScrolledRef = useRef(false);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD;
    userScrolledRef.current = !atBottom;
    if (atBottom) setShowNewMessages(false);
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
    if (!userScrolledRef.current) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else {
      setShowNewMessages(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    userScrolledRef.current = false;
    setShowNewMessages(false);
  }, []);

  return { containerRef, showNewMessages, scrollToBottom };
}
