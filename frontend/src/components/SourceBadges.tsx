interface SourceBadgesProps {
  sources: string[];
}

export function SourceBadges({ sources }: SourceBadgesProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {sources.map((src) => (
        <span
          key={src}
          title={src}
          className="
            max-w-[18rem] truncate rounded-full border border-indigo-700/60
            bg-indigo-900/30 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300
          "
        >
          {src}
        </span>
      ))}
    </div>
  );
}
