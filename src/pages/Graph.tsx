import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ChevronDown, Network, Sparkles, X } from 'lucide-react';
import { GraphCanvas, GraphLegend, graphKindColor } from '../components/cyber/GraphCanvas';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { MonitoringStatus } from '../components/layout/Header';
import { graphLegend } from '../data/graph';
import { getOrganizationGraph } from '../services/api';
import { useApiResource } from '../hooks/useApiResource';
import { AsyncSection } from '../components/common/AsyncSection';
import { cn } from '../utils/cn';
import type { GraphNode, GraphNodeKind } from '../types/domain';

/** Maximum nodes rendered on the canvas at any one time. */
const NODE_CAP = 50;

const CLUSTER_OPTIONS: { id: GraphNodeKind | 'all'; label: string }[] = [
  { id: 'all',          label: 'Overview (mixed)' },
  { id: 'employee',    label: 'Employees' },
  { id: 'iam',         label: 'IAM accounts' },
  { id: 'device',      label: 'Devices' },
  { id: 'application', label: 'Applications' },
  { id: 'cloud',       label: 'Cloud assets' },
  { id: 'vendor',      label: 'Vendors' },
  { id: 'policy',      label: 'Policies' },
  { id: 'control',     label: 'Controls' },
  { id: 'finding',     label: 'Findings' },
  { id: 'evidence',    label: 'Evidence' },
];

export function Graph() {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [cluster, setCluster] = useState<GraphNodeKind | 'all'>('all');
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // One call returns the whole topology — slicing happens client-side.
  const state = useApiResource(
    () => getOrganizationGraph({ scope: 'full', limit_employees: 60, include_vendors: true }),
    []
  );

  const allNodes = state.data?.nodes ?? [];
  const allEdges = state.data?.edges ?? [];

  /** Fast id-based lookup across the full dataset. */
  const byId = useMemo(() => new Map(allNodes.map((n) => [n.id, n])), [allNodes]);

  /**
   * Build the visible slice — stays within NODE_CAP.
   *
   * Blast-radius mode (node selected):
   *   Show the selected node + all direct neighbours (capped at NODE_CAP).
   *
   * Cluster mode (no selection):
   *   'all'  → balanced sample across every kind.
   *   <kind> → up to NODE_CAP nodes of that kind.
   */
  const { visibleNodes, visibleEdges } = useMemo(() => {
    let seeds: GraphNode[];

    if (selected) {
      const keep = new Set<string>([selected.id]);
      for (const e of allEdges) {
        if (e.from === selected.id) keep.add(e.to);
        if (e.to === selected.id) keep.add(e.from);
      }
      seeds = allNodes.filter((n) => keep.has(n.id)).slice(0, NODE_CAP);
    } else if (cluster === 'all') {
      // Even spread: a few nodes per kind
      const perKind = Math.max(1, Math.floor(NODE_CAP / (CLUSTER_OPTIONS.length - 1)));
      const groups = new Map<string, GraphNode[]>();
      for (const n of allNodes) {
        const bucket = groups.get(n.kind) ?? [];
        if (bucket.length < perKind) { bucket.push(n); groups.set(n.kind, bucket); }
      }
      seeds = Array.from(groups.values()).flat().slice(0, NODE_CAP);
    } else {
      seeds = allNodes.filter((n) => n.kind === cluster).slice(0, NODE_CAP);
    }

    const seedIds = new Set(seeds.map((n) => n.id));
    const edges = allEdges.filter((e) => seedIds.has(e.from) && seedIds.has(e.to));
    return { visibleNodes: seeds, visibleEdges: edges };
  }, [selected, cluster, allNodes, allEdges]);

  /** Full neighbour list for the selection panel (not capped — shown as a scrollable list). */
  const neighbours = useMemo(() => {
    if (!selected) return [];
    return allEdges
      .filter((e) => e.from === selected.id || e.to === selected.id)
      .map((e) => {
        const other = e.from === selected.id ? e.to : e.from;
        return { node: byId.get(other), risky: e.kind === 'risk' };
      })
      .filter((n): n is { node: GraphNode; risky: boolean } => Boolean(n.node));
  }, [selected, byId, allEdges]);

  const criticalCount = allNodes.filter((n) => n.severity === 'critical').length;
  const activeLabel = CLUSTER_OPTIONS.find((o) => o.id === cluster)?.label ?? 'Overview';

  if (state.status !== 'success') {
    return <AsyncSection state={state}>{() => null}</AsyncSection>;
  }

  return (
    <div className="relative flex h-full flex-col">
      {/* ── Command bar ─────────────────────────────────────────────── */}
      <div className="glass relative z-20 flex flex-wrap items-center gap-3 border-b border-border px-5 py-3">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-base font-semibold tracking-tight">
            <Network className="h-4 w-4 text-primary" aria-hidden />
            Organization Graph
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {selected
              ? `Blast radius · ${visibleNodes.length} nodes · ${visibleEdges.length} edges`
              : `Showing ${visibleNodes.length} of ${allNodes.length} entities · ${visibleEdges.length} edges visible`}
          </p>
        </div>

        <div className="flex-1" />

        {/* ── Cluster picker ── */}
        <div className="relative">
          <button
            id="cluster-picker"
            type="button"
            onClick={() => setDropdownOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface-2/60 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{
                backgroundColor:
                  cluster === 'all' ? 'var(--primary)' : graphKindColor[cluster as GraphNodeKind],
              }}
              aria-hidden
            />
            {activeLabel}
            <ChevronDown
              className={cn(
                'h-3.5 w-3.5 text-muted-foreground transition-transform',
                dropdownOpen && 'rotate-180'
              )}
            />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full z-50 mt-1.5 w-52 overflow-hidden rounded-xl border border-border bg-card shadow-xl">
              {CLUSTER_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setCluster(opt.id);
                    setSelected(null);
                    setDropdownOpen(false);
                  }}
                  className={cn(
                    'flex w-full items-center gap-2.5 px-3.5 py-2 text-left text-[13px] transition-colors',
                    opt.id === cluster
                      ? 'bg-primary/10 font-medium text-primary'
                      : 'text-foreground hover:bg-accent'
                  )}
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        opt.id === 'all'
                          ? 'var(--primary)'
                          : graphKindColor[opt.id as GraphNodeKind],
                    }}
                    aria-hidden
                  />
                  {opt.label}
                  <span className="ml-auto font-mono text-2xs text-muted-foreground">
                    {opt.id === 'all'
                      ? allNodes.length
                      : allNodes.filter((n) => n.kind === opt.id).length}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <Badge tone="danger" dot>
          {criticalCount} critical
        </Badge>
        <MonitoringStatus compact />
        <Link to="/copilot">
          <Button variant="ai" size="sm" iconLeft={<Sparkles className="h-3.5 w-3.5" />}>
            Explain this graph
          </Button>
        </Link>
      </div>

      {/* ── Canvas ──────────────────────────────────────────────────── */}
      <div
        className="relative min-h-0 flex-1"
        onClick={() => { if (dropdownOpen) setDropdownOpen(false); }}
      >
        <GraphCanvas
          nodes={visibleNodes}
          edges={visibleEdges}
          selectedId={selected?.id ?? null}
          onSelect={setSelected}
          className="h-full w-full"
        />

        {/* Blast-radius banner */}
        {selected && (
          <div className="pointer-events-none absolute inset-x-0 top-3 flex justify-center">
            <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1.5 text-xs font-medium text-primary shadow">
              Blast radius · {visibleNodes.length} connected nodes
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="ml-1 rounded-full p-0.5 transition-colors hover:bg-primary/20"
                aria-label="Exit blast radius mode"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-4">
          <div className="pointer-events-auto rounded-xl border border-border bg-card/85 px-4 py-2.5 backdrop-blur">
            <GraphLegend items={graphLegend} />
          </div>
        </div>

        {/* Selection panel */}
        {selected && (
          <motion.aside
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            aria-label={`${selected.label} details`}
            className="absolute right-4 top-12 w-[300px] overflow-hidden rounded-xl border border-border bg-card/95 shadow-lg backdrop-blur"
          >
            <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: graphKindColor[selected.kind] }}
                    aria-hidden
                  />
                  {selected.kind}
                </p>
                <p className="mt-1 truncate text-sm font-semibold">{selected.label}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                aria-label="Clear selection"
                className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="px-4 py-3">
              <p className="text-xs leading-relaxed text-muted-foreground">{selected.meta}</p>
              {selected.severity && (
                <div className="mt-2.5">
                  <RiskBadge level={selected.severity} />
                </div>
              )}
            </div>

            <div className="border-t border-border px-4 py-3">
              <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                Connected entities · {neighbours.length}
              </p>
              <ul className="mt-2 max-h-[280px] space-y-1.5 overflow-y-auto">
                {neighbours.map(({ node, risky }) => (
                  <li key={node.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(node)}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors duration-150',
                        risky
                          ? 'border-risk-critical/30 bg-risk-critical/[0.06] hover:bg-risk-critical/[0.10]'
                          : 'border-border bg-surface-2/50 hover:bg-accent/60'
                      )}
                    >
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ backgroundColor: graphKindColor[node.kind] }}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px] font-medium">{node.label}</span>
                        <span className="block truncate text-2xs text-muted-foreground">{node.meta}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </motion.aside>
        )}
      </div>
    </div>
  );
}