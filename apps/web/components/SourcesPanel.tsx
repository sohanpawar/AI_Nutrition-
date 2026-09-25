import type { Claim } from "@/lib/types";

type SourcesPanelProps = {
  claims: Claim[];
};

/**
 * Milestone 1: sources stay null → panel shows empty state.
 * Milestone 2: non-null claim.source values render as citations.
 */
export function SourcesPanel({ claims }: SourcesPanelProps) {
  const sources = claims
    .map((claim) => claim.source)
    .filter((source): source is string => Boolean(source && source.trim()));

  return (
    <aside className="sources-panel" aria-label="Sources">
      <h2 className="sources-title">Sources</h2>
      {sources.length === 0 ? (
        <p className="sources-empty">
          Sources will appear here when citations are available.
        </p>
      ) : (
        <ol className="sources-list">
          {sources.map((source, index) => (
            <li key={`${source}-${index}`}>
              <a href={source} target="_blank" rel="noopener noreferrer">
                {source}
              </a>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
