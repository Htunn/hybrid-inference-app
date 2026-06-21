import type { RagDocument } from '../services/ragApi';

interface DocumentListProps {
  documents: RagDocument[];
  onDelete: (id: number) => Promise<void>;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="text-xs text-slate-500 px-1">
        No documents ingested yet. Upload a file to get started.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1.5">
      {documents.map((doc) => (
        <li
          key={doc.id}
          className="flex items-start justify-between gap-2 rounded-lg bg-slate-800 px-3 py-2.5"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-200" title={doc.file_path}>
              {doc.title ?? doc.file_path}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              {doc.file_path !== (doc.title ?? doc.file_path) && (
                <span className="mr-2 truncate">{doc.file_path}</span>
              )}
              {formatDate(doc.ingested_at)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onDelete(doc.id)}
            aria-label={`Delete ${doc.file_path}`}
            className="shrink-0 rounded p-1 text-slate-500 transition hover:bg-red-900/40 hover:text-red-400"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </li>
      ))}
    </ul>
  );
}
