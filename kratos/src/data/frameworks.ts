import type { Framework } from '../types/domain';

export const frameworks: Framework[] = [
{
  id: 'fw-eu-ai-act',
  name: 'EU Artificial Intelligence Act',
  shortName: 'EU AI Act',
  authority: 'European Commission',
  coverage: 86,
  controlsTotal: 214,
  controlsPassing: 184,
  controlsFailing: 30,
  status: 'at-risk',
  nextAudit: '2026-08-21',
  owner: 'Legal & Compliance'
},
{
  id: 'fw-iso-42001',
  name: 'ISO/IEC 42001 — AI Management System',
  shortName: 'ISO 42001',
  authority: 'ISO',
  coverage: 72,
  controlsTotal: 158,
  controlsPassing: 114,
  controlsFailing: 44,
  status: 'at-risk',
  nextAudit: '2026-09-04',
  owner: 'AI Governance Office'
},
{
  id: 'fw-nist-airmf',
  name: 'NIST AI Risk Management Framework',
  shortName: 'NIST AI RMF',
  authority: 'NIST',
  coverage: 91,
  controlsTotal: 132,
  controlsPassing: 120,
  controlsFailing: 12,
  status: 'compliant',
  nextAudit: '2026-11-12',
  owner: 'AI Governance Office'
},
{
  id: 'fw-soc2',
  name: 'SOC 2 Type II',
  shortName: 'SOC 2',
  authority: 'AICPA',
  coverage: 96,
  controlsTotal: 168,
  controlsPassing: 161,
  controlsFailing: 7,
  status: 'compliant',
  nextAudit: '2026-09-29',
  owner: 'Security Engineering'
},
{
  id: 'fw-gdpr',
  name: 'General Data Protection Regulation',
  shortName: 'GDPR',
  authority: 'EU DPAs',
  coverage: 89,
  controlsTotal: 142,
  controlsPassing: 126,
  controlsFailing: 16,
  status: 'compliant',
  nextAudit: '2026-10-08',
  owner: 'Privacy Office'
},
{
  id: 'fw-hipaa',
  name: 'HIPAA Security Rule',
  shortName: 'HIPAA',
  authority: 'HHS OCR',
  coverage: 64,
  controlsTotal: 96,
  controlsPassing: 61,
  controlsFailing: 35,
  status: 'non-compliant',
  nextAudit: '2026-10-30',
  owner: 'Privacy Office'
},
{
  id: 'fw-iso-27001',
  name: 'ISO/IEC 27001',
  shortName: 'ISO 27001',
  authority: 'ISO',
  coverage: 93,
  controlsTotal: 186,
  controlsPassing: 173,
  controlsFailing: 13,
  status: 'compliant',
  nextAudit: '2026-12-02',
  owner: 'Security Engineering'
},
{
  id: 'fw-dora',
  name: 'Digital Operational Resilience Act',
  shortName: 'DORA',
  authority: 'ESAs',
  coverage: 41,
  controlsTotal: 118,
  controlsPassing: 48,
  controlsFailing: 70,
  status: 'not-assessed',
  nextAudit: '2027-01-15',
  owner: 'Resilience Program'
}];


export const controlDomains = [
{ domain: 'Risk management', passing: 42, failing: 4 },
{ domain: 'Data governance', passing: 38, failing: 9 },
{ domain: 'Technical documentation', passing: 26, failing: 12 },
{ domain: 'Record keeping', passing: 31, failing: 3 },
{ domain: 'Transparency', passing: 24, failing: 8 },
{ domain: 'Human oversight', passing: 19, failing: 11 },
{ domain: 'Accuracy & robustness', passing: 33, failing: 6 }];