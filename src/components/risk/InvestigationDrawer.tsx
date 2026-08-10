import { ExternalLink, Sparkles } from 'lucide-react';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';
import { Badge, RiskBadge } from '../ui/Badge';
import { ProgressBar } from '../ui/Progress';
import { InvestigationChain } from '../cyber/InvestigationChain';
import { ConfidenceMeter, RiskStatusBadge } from '../common/StatusPills';
import { formatRelative } from '../../utils/format';
import { cn } from '../../utils/cn';
import type { RiskItem } from '../../types/domain';

/**
 * The investigation workspace. Opens from any risk row, top-risk card or
 * finding and shows the full POLICY → … → RECOMMENDATION chain.
 */
export function InvestigationDrawer({
  risk,
  onClose



}: {risk: RiskItem | null;onClose: () => void;}) {
  return (
    <Drawer
      open={Boolean(risk)}
      onClose={onClose}
      width="xl"
      title={risk?.title ?? ''}
      subtitle={risk ? `${risk.id} · ${risk.assetType} · updated ${formatRelative(risk.updatedAt)}` : undefined}
      eyebrow={
      risk ?
      <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={risk.severity} />
            <RiskStatusBadge status={risk.status} />
            <Badge tone="neutral">{risk.framework}</Badge>
            <Badge tone="primary">{risk.control}</Badge>
          </div> :
      undefined
      }
      footer={
      <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button variant="outline" iconLeft={<ExternalLink className="h-4 w-4" />}>
            Open in graph
          </Button>
          <Button variant="ai" iconLeft={<Sparkles className="h-4 w-4" />}>
            Auto-remediate
          </Button>
        </>
      }>
      
      {risk &&
      <div className="space-y-6">
          {/* Score header */}
          <div className="relative overflow-hidden rounded-xl border border-border bg-surface-2/50 p-5">
            <div className="absolute inset-0 cyber-grid-fine opacity-40" aria-hidden />
            <div className="relative flex flex-wrap items-end justify-between gap-5">
              <div>
                <p className="text-2xs font-semibold uppercase tracking-label text-muted-foreground">
                  Risk score
                </p>
                <p
                className={cn(
                  'mt-1 font-mono text-5xl font-semibold leading-none tracking-tight',
                  risk.score >= 90 ?
                  'text-risk-critical' :
                  risk.score >= 75 ?
                  'text-risk-high' :
                  'text-risk-medium'
                )}>
                
                  {risk.score}
                  <span className="text-lg font-normal text-muted-foreground"> / 100</span>
                </p>
                <p className="mt-2 text-2xs font-semibold uppercase tracking-label text-risk-critical">
                  {risk.severity}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-[13px]">
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Owner
                  </dt>
                  <dd className="mt-0.5 font-medium">{risk.owner}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Department
                  </dt>
                  <dd className="mt-0.5 font-medium">{risk.department}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Asset
                  </dt>
                  <dd className="mt-0.5 truncate font-mono text-xs">{risk.asset}</dd>
                </div>
                <div>
                  <dt className="text-2xs uppercase tracking-label text-muted-foreground">
                    Sentinel confidence
                  </dt>
                  <dd className="mt-1">
                    <ConfidenceMeter value={risk.aiConfidence ?? 0} />
                  </dd>
                </div>
              </dl>
            </div>
            <div className="relative mt-5 grid gap-3 sm:grid-cols-2">
              <ProgressBar
              label="Likelihood"
              value={risk.likelihood * 20}
              tone="warning"
              showValue />
            
              <ProgressBar label="Impact" value={risk.impact * 20} tone="danger" showValue />
            </div>
          </div>

          {/* Investigation chain */}
          <div>
            <p className="mb-3 flex items-center gap-2 text-2xs font-semibold uppercase tracking-label text-muted-foreground">
              Investigation chain
              <span className="h-px flex-1 bg-border" aria-hidden />
            </p>
            <InvestigationChain chain={risk.chain} />
          </div>
        </div>
      }
    </Drawer>);

}