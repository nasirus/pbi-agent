export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: JSX.Element;
}): JSX.Element {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      {description ? <div className="empty-state__description">{description}</div> : null}
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}
