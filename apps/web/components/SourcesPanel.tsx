import type { Claim } from "@/lib/types";
import { BookIcon } from "./Icons";

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
    <aside className="sources-panel panel-glass" aria-label="Sources">
      <div className="sources-heading">
        <BookIcon size={18} />
        <h2 className="sources-title">Sources</h2>
      </div>
      {sources.length === 0 ? (
        <div className="sources-empty-card">
          <p className="sources-empty">
            Citations will show here in Milestone 2. For now, answers stay
            structured with claims but no linked sources.
          </p>
        </div>
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
