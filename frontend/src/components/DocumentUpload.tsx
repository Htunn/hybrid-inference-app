import { useCallback, useRef, useState } from 'react';

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

const ACCEPTED = '.md,.txt,.pdf';
const ACCEPTED_TYPES = new Set(['text/markdown', 'text/plain', 'application/pdf']);

export function DocumentUpload({ onUpload, isUploading }: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      // Basic client-side type check before sending
      const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
      if (!ACCEPTED_TYPES.has(file.type) && !['md', 'txt', 'pdf'].includes(ext)) {
        setLastResult('Unsupported file type. Upload a .md, .txt, or .pdf file.');
        return;
      }
      setLastResult(null);
      try {
        await onUpload(file);
        setLastResult(`"${file.name}" ingested successfully.`);
      } catch {
        // Error is surfaced via the hook's error state — no double-toast needed
        setLastResult(null);
      }
    },
    [onUpload],
  );

  const onInputChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) await handleFile(file);
      // Reset so the same file can be re-uploaded after deletion
      if (inputRef.current) inputRef.current.value = '';
    },
    [handleFile],
  );

  const onDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) await handleFile(file);
    },
    [handleFile],
  );

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        disabled={isUploading}
        className={`
          flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed
          px-4 py-6 text-sm transition
          ${isDragging
            ? 'border-indigo-400 bg-indigo-900/20 text-indigo-300'
            : 'border-slate-600 bg-slate-800/50 text-slate-400 hover:border-indigo-500 hover:text-slate-300'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        {isUploading ? (
          <>
            <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-400 border-t-indigo-400" />
            <span>Ingesting…</span>
          </>
        ) : (
          <>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-7 w-7"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v-8m0 0-3 3m3-3 3 3M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1" />
            </svg>
            <span>
              Drag &amp; drop or <span className="text-indigo-400 font-medium">browse</span>
            </span>
            <span className="text-xs text-slate-500">.md · .txt · .pdf (max 10 MB)</span>
          </>
        )}
      </button>

      {lastResult && (
        <p className="text-xs text-emerald-400 px-1">{lastResult}</p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        aria-label="Upload document"
        className="hidden"
        onChange={onInputChange}
      />
    </div>
  );
}
