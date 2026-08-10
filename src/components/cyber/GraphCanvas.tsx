import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import type { GraphEdge, GraphNode, GraphNodeKind } from '../../types/domain';

/** Full CSS colors so they can be used directly in SVG style properties. */
export const graphKindColor: Record<GraphNodeKind, string> = {
  employee: 'oklch(var(--chart-2))',
  iam: 'oklch(var(--primary))',
  device: 'oklch(var(--chart-4))',
  application: 'oklch(var(--cyan))',
  cloud: 'oklch(var(--chart-1))',
  vendor: 'oklch(var(--chart-5))',
  policy: 'oklch(var(--ai))',
  control: 'oklch(var(--chart-3))',
  finding: 'oklch(var(--risk-critical))',
  evidence: 'oklch(var(--success))'
};

const VIEW_W = 1000;
const VIEW_H = 640;

/**
 * Interactive organization intelligence map. Selecting a node dims everything
 * not connected to it, so the graph communicates real relationships rather
 * than decoration.
 */
export function GraphCanvas({
  nodes,
  edges,
  selectedId,
  onSelect,
  className






}: {nodes: GraphNode[];edges: GraphEdge[];selectedId?: string | null;onSelect?: (node: GraphNode | null) => void;className?: string;}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const focus = selectedId ?? hovered;

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const connected = useMemo(() => {
    if (!focus) return null;
    const set = new Set<string>([focus]);
    edges.forEach((edge) => {
      if (edge.from === focus) set.add(edge.to);
      if (edge.to === focus) set.add(edge.from);
    });
    return set;
  }, [focus, edges]);

  const isDim = (id: string) => Boolean(connected && !connected.has(id));

  return (
    <div className={cn('relative overflow-hidden', className)}>
      <div className="absolute inset-0 cyber-grid mask-fade opacity-60" aria-hidden />
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="relative h-full w-full"
        role="application"
        aria-label="Organization relationship graph"
        onClick={() => onSelect?.(null)}>
        
        <defs>
          <filter id="node-glow" x="-70%" y="-70%" width="240%" height="240%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Relationship paths */}
        {edges.map((edge, i) => {
          const a = byId.get(edge.from);
          const b = byId.get(edge.to);
          if (!a || !b) return null;
          const dim = isDim(edge.from) || isDim(edge.to);
          const risky = edge.kind === 'risk';
          const active = focus !== null && (edge.from === focus || edge.to === focus);
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2 - 24;

          return (
            <motion.path
              key={`${edge.from}-${edge.to}-${i}`}
              d={`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`}
              fill="none"
              stroke={risky ? 'oklch(var(--risk-critical))' : 'oklch(var(--primary))'}
              strokeWidth={active ? 1.9 : 1.1}
              strokeDasharray={risky ? '5 5' : undefined}
              className={cn(risky && active && 'motion-safe:animate-dash-flow')}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: dim ? 0.07 : active ? 0.85 : 0.28 }}
              transition={{ duration: 0.7, delay: Math.min(0.5, i * 0.02) }} />);


        })}

        {/* Nodes */}
        {nodes.map((node, i) => {
          const dim = isDim(node.id);
          const isFocus = focus === node.id;
          const color =
          node.severity === 'critical' ?
          'oklch(var(--risk-critical))' :
          graphKindColor[node.kind];
          const r = node.kind === 'employee' || node.kind === 'evidence' ? 7 : 9;

          return (
            <motion.g
              key={node.id}
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: dim ? 0.18 : 1, scale: 1 }}
              transition={{ duration: 0.32, delay: Math.min(0.6, i * 0.02) }}
              style={{ cursor: 'pointer' }}
              tabIndex={0}
              role="button"
              aria-label={`${node.kind}: ${node.label}. ${node.meta}`}
              onClick={(event) => {
                event.stopPropagation();
                onSelect?.(node);
              }}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelect?.(node);
                }
              }}>
              
              {node.severity === 'critical' && !dim &&
              <circle
                cx={node.x}
                cy={node.y}
                r={r + 8}
                style={{ fill: 'oklch(var(--risk-critical) / 0.14)' }}
                className="motion-safe:animate-signal-pulse" />

              }
              <circle
                cx={node.x}
                cy={node.y}
                r={isFocus ? r + 4 : r}
                style={{
                  fill: 'oklch(var(--background))',
                  stroke: color,
                  strokeWidth: isFocus ? 2.6 : 1.6,
                  filter:
                  isFocus || node.severity === 'critical' ? 'url(#node-glow)' : undefined
                }} />
              
              <circle
                cx={node.x}
                cy={node.y}
                r={isFocus ? 3.4 : 2.6}
                style={{ fill: color }} />
              
              <text
                x={node.x}
                y={node.y + r + 14}
                textAnchor="middle"
                className="pointer-events-none select-none"
                style={{
                  fill: 'oklch(var(--muted-foreground))',
                  fontSize: 10,
                  fontWeight: isFocus ? 600 : 500
                }}>
                
                {node.label}
              </text>
            </motion.g>);

        })}
      </svg>
    </div>);

}

export function GraphLegend({
  items,
  className



}: {items: {kind: GraphNodeKind;label: string;}[];className?: string;}) {
  return (
    <ul className={cn('flex flex-wrap items-center gap-x-4 gap-y-2', className)}>
      {items.map((item) =>
      <li key={item.kind} className="flex items-center gap-1.5">
          <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: graphKindColor[item.kind] }}
          aria-hidden />
        
          <span className="text-2xs text-muted-foreground">{item.label}</span>
        </li>
      )}
    </ul>);

}