import type { Policy } from '../types/domain';

export const policies: Policy[] = [
{
  id: 'POL-041',
  name: 'Access Control Policy',
  framework: 'ISO 27001',
  owner: 'Dana Okafor',
  controls: 18,
  status: 'published',
  lastReviewed: '2026-06-14',
  nextReview: '2026-12-14',
  aiGenerated: false
},
{
  id: 'POL-039',
  name: 'Cloud Security Standard',
  framework: 'ISO 27001',
  owner: 'Kenji Tanaka',
  controls: 24,
  status: 'published',
  lastReviewed: '2026-07-02',
  nextReview: '2027-01-02',
  aiGenerated: true
},
{
  id: 'POL-036',
  name: 'DPDP Privacy Policy',
  framework: 'DPDP',
  owner: 'Maya Lindqvist',
  controls: 16,
  status: 'in-review',
  lastReviewed: '2026-08-05',
  nextReview: '2027-02-05',
  aiGenerated: true
},
{
  id: 'POL-033',
  name: 'Third-Party Risk Policy',
  framework: 'SOC 2',
  owner: 'Aisha Bello',
  controls: 12,
  status: 'published',
  lastReviewed: '2026-05-28',
  nextReview: '2026-11-28',
  aiGenerated: false
},
{
  id: 'POL-030',
  name: 'Monitoring & Logging Policy',
  framework: 'SOC 2',
  owner: 'Security Engineering',
  controls: 14,
  status: 'published',
  lastReviewed: '2026-06-30',
  nextReview: '2026-12-30',
  aiGenerated: false
},
{
  id: 'POL-028',
  name: 'Data Retention Standard',
  framework: 'DPDP',
  owner: 'Kenji Tanaka',
  controls: 9,
  status: 'in-review',
  lastReviewed: '2026-08-06',
  nextReview: '2027-02-06',
  aiGenerated: true
},
{
  id: 'POL-024',
  name: 'Endpoint Hardening Standard',
  framework: 'Internal Controls',
  owner: 'Security Engineering',
  controls: 11,
  status: 'published',
  lastReviewed: '2026-04-18',
  nextReview: '2026-10-18',
  aiGenerated: false
},
{
  id: 'POL-021',
  name: 'Change Management Policy',
  framework: 'Internal Controls',
  owner: 'Rohan Bhatt',
  controls: 8,
  status: 'draft',
  lastReviewed: '2026-06-18',
  nextReview: '2026-12-18',
  aiGenerated: false
},
{
  id: 'POL-017',
  name: 'AI Incident Response Playbook',
  framework: 'SOC 2',
  owner: 'Dana Okafor',
  controls: 10,
  status: 'draft',
  lastReviewed: '2026-07-21',
  nextReview: '2027-01-21',
  aiGenerated: true
},
{
  id: 'POL-012',
  name: 'Legacy Chatbot Governance',
  framework: 'Internal Controls',
  owner: 'Rohan Bhatt',
  controls: 4,
  status: 'archived',
  lastReviewed: '2025-11-02',
  nextReview: '—',
  aiGenerated: false
}];


/** Stages rendered by the policy ingestion / analysis animation. */
export const policyPipeline = [
{ id: 'upload', label: 'Upload', detail: 'Document received · SHA-256 recorded' },
{ id: 'analyzing', label: 'Analyzing', detail: 'Sentinel parsing clauses and obligations' },
{ id: 'controls', label: 'Controls extracted', detail: '18 candidate controls identified' },
{ id: 'mapped', label: 'Requirements mapped', detail: 'Mapped to ISO 27001 · SOC 2 · DPDP' },
{ id: 'evidence', label: 'Evidence identified', detail: '11 evidence requirements generated' }];