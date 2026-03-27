export function LoadingSpinner({
  size = "md",
}: {
  size?: "sm" | "md" | "lg";
}): JSX.Element {
  const cls = size === "md" ? "spinner" : `spinner spinner--${size}`;
  return <div className={cls} />;
}
