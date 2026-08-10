import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { CornerDownLeft, Search, Sparkles } from 'lucide-react';

import { cn } from '../../utils/cn';
import { navigation } from '../../data/navigation';
import { risks } from '../../data/risks';
import { controls, findings } from '../../data/controls';
import { policies } from '../../data/policies';
import { evidenceItems } from '../../data/evidence';
import {
  applications,
  cloudAssets,
  devices,
  employees,
  vendors,
} from '../../data/organization';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Kbd } from '../ui/Controls';

interface Command {
  id: string;
  label: string;
  group: string;
  hint?: string;
  to: string;
  ai?: boolean;
}

/** One flat searchable index across every entity in the estate. */
function buildIndex(): Command[] {
  return [
    {
      id: 'ai-ask',
      label: 'Ask Sentinel AI a question',
      group: 'Sentinel AI',
      hint: 'Copilot',
      to: '/copilot',
      ai: true,
    },
    {
      id: 'ai-report',
      label: 'Generate audit report',
      group: 'Sentinel AI',
      hint: 'Reports',
      to: '/reports',
      ai: true,
    },

    ...navigation.flatMap((group) =>
      group.items.map((item) => ({
        id: `nav-${item.to}`,
        label: item.label,
        group: 'Navigate',
        hint: group.label,
        to: item.to,
      }))
    ),

    ...risks.map((r) => ({
      id: `risk-${r.id}`,
      label: `${r.id} · ${r.title}`,
      group: 'Risks',
      hint: `${r.severity} · ${r.owner}`,
      to: '/risk',
    })),

    ...findings.map((f) => ({
      id: `finding-${f.id}`,
      label: `${f.id} · ${f.title}`,
      group: 'Findings',
      hint: f.control,
      to: '/findings',
    })),

    ...controls.map((c) => ({
      id: `control-${c.id}`,
      label: `${c.id} · ${c.name}`,
      group: 'Controls',
      hint: c.framework,
      to: '/controls',
    })),

    ...policies.map((p) => ({
      id: `policy-${p.id}`,
      label: p.name,
      group: 'Policies',
      hint: p.framework,
      to: '/policies',
    })),

    ...employees.map((e) => ({
      id: `emp-${e.id}`,
      label: e.name,
      group: 'Employees',
      hint: `${e.department} · ${e.role}`,
      to: '/org/employees',
    })),

    ...devices.map((d) => ({
      id: `dev-${d.id}`,
      label: d.id,
      group: 'Devices',
      hint: `${d.owner} · ${d.os}`,
      to: '/org/devices',
    })),

    ...applications.map((a) => ({
      id: `app-${a.id}`,
      label: a.name,
      group: 'Applications',
      hint: `${a.criticality} · ${a.owner}`,
      to: '/org/applications',
    })),

    ...cloudAssets.map((c) => ({
      id: `cld-${c.id}`,
      label: c.resource,
      group: 'Cloud Assets',
      hint: `${c.provider} · ${c.region}`,
      to: '/org/cloud',
    })),

    ...vendors.map((v) => ({
      id: `ven-${v.id}`,
      label: v.name,
      group: 'Vendors',
      hint: `${v.category} · risk ${v.riskScore}`,
      to: '/org/vendors',
    })),

    ...evidenceItems.map((e) => ({
      id: `ev-${e.id}`,
      label: `${e.id} · ${e.name}`,
      group: 'Evidence',
      hint: e.control,
      to: '/evidence',
    })),
  ];
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({
  open,
  onClose,
}: CommandPaletteProps) {
  const navigate = useNavigate();

  const ref = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  useFocusTrap(ref, open, onClose);

  const index = useMemo(buildIndex, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();

    if (!q) {
      return index
        .filter(
          (c) => c.group === 'Sentinel AI' || c.group === 'Navigate'
        )
        .slice(0, 9);
    }

    return index
      .filter(
        (c) =>
          c.label.toLowerCase().includes(q) ||
          c.group.toLowerCase().includes(q) ||
          (c.hint ?? '').toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [index, query]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    if (!open) {
      setQuery('');
    }
  }, [open]);

  const run = (command: Command) => {
    navigate(command.to);
    onClose();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();

      setActive(
        (i) => (i + 1) % Math.max(1, results.length)
      );
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();

      setActive(
        (i) =>
          (i - 1 + results.length) %
          Math.max(1, results.length)
      );
    }

    if (event.key === 'Enter' && results[active]) {
      event.preventDefault();
      run(results[active]);
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
    }
  };

  let lastGroup = '';

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            onClick={onClose}
            className="absolute inset-0 bg-background/75 backdrop-blur-md"
            aria-hidden
          />

          {/* Dialog */}
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-label="Global search"
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.99 }}
            transition={{
              duration: 0.2,
              ease: [0.22, 1, 0.36, 1],
            }}
            onKeyDown={onKeyDown}
            className="relative w-full max-w-xl overflow-hidden rounded-xl border border-border bg-popover shadow-xl"
          >
            <div className="flex items-center gap-3 border-b border-border px-4">
              <Search
                className="h-4 w-4 shrink-0 text-primary"
                aria-hidden
              />

              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search employees, devices, cloud, vendors, controls, evidence…"
                aria-label="Search everything"
                className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />

              <Kbd>Esc</Kbd>
            </div>

            <ul
              role="listbox"
              aria-label="Results"
              className="max-h-[54vh] overflow-y-auto p-2"
            >
              {results.length === 0 && (
                <li className="px-3 py-10 text-center text-sm text-muted-foreground">
                  No entity matches “{query}”
                </li>
              )}

              {results.map((command, i) => {
                const showGroup = command.group !== lastGroup;
                lastGroup = command.group;

                return (
                  <Fragment key={command.id}>
                    {showGroup && (
                      <li
                        aria-hidden
                        className="px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-label text-muted-foreground"
                      >
                        {command.group}
                      </li>
                    )}

                    <li
                      role="option"
                      aria-selected={i === active}
                    >
                      <button
                        type="button"
                        onMouseEnter={() => setActive(i)}
                        onClick={() => run(command)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-[13px] transition-colors duration-150',
                          i === active
                            ? 'bg-primary/10'
                            : 'hover:bg-accent/60'
                        )}
                      >
                        {command.ai && (
                          <Sparkles
                            className="h-3.5 w-3.5 shrink-0 text-ai"
                            aria-hidden
                          />
                        )}

                        <span className="flex-1 truncate font-medium">
                          {command.label}
                        </span>

                        {command.hint && (
                          <span className="shrink-0 font-mono text-2xs text-muted-foreground">
                            {command.hint}
                          </span>
                        )}

                        {i === active && (
                          <CornerDownLeft
                            className="h-3.5 w-3.5 shrink-0 text-primary"
                            aria-hidden
                          />
                        )}
                      </button>
                    </li>
                  </Fragment>
                );
              })}
            </ul>

            <div className="flex items-center justify-between border-t border-border bg-surface-2/60 px-4 py-2 text-2xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Kbd>↑</Kbd>
                <Kbd>↓</Kbd>
                navigate
              </span>

              <span className="font-mono">
                {results.length} results
              </span>

              <span className="flex items-center gap-1.5">
                <Kbd>↵</Kbd>
                open
              </span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}