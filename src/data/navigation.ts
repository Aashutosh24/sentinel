import {
  Activity,
  Boxes,
  Cloud,
  Cpu,
  FileBadge,
  FileBarChart,
  FileText,
  Fingerprint,
  Gauge,
  Handshake,
  Laptop,
  LayoutDashboard,
  ScanSearch,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Network,
  Users,
  type LucideIcon } from
'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  tone?: 'ai' | 'critical';
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navigation: NavGroup[] = [
{
  label: 'Overview',
  items: [{ to: '/', label: 'Command Center', icon: LayoutDashboard }]
},
{
  label: 'Intelligence',
  items: [
  { to: '/copilot', label: 'Sentinel AI', icon: Sparkles, tone: 'ai' },
  { to: '/investigations', label: 'Investigations', icon: ScanSearch },
  { to: '/graph', label: 'Organization Graph', icon: Network }]

},
{
  label: 'Governance',
  items: [
  { to: '/policies', label: 'Policies', icon: FileText },
  { to: '/controls', label: 'Controls', icon: ShieldCheck },
  { to: '/frameworks', label: 'Frameworks', icon: ScrollText }]

},
{
  label: 'Risk',
  items: [
  { to: '/risk', label: 'Risk Center', icon: ShieldAlert, badge: '4', tone: 'critical' },
  { to: '/findings', label: 'Findings', icon: Gauge, badge: '23' }]

},
{
  label: 'Organization',
  items: [
  { to: '/org/employees', label: 'Employees', icon: Users },
  { to: '/org/identity', label: 'Identity & Access', icon: Fingerprint },
  { to: '/org/devices', label: 'Devices', icon: Laptop },
  { to: '/org/applications', label: 'Applications', icon: Boxes },
  { to: '/org/cloud', label: 'Cloud Assets', icon: Cloud },
  { to: '/org/vendors', label: 'Third-Party Vendors', icon: Handshake }]

},
{
  label: 'Privacy',
  items: [
  { to: '/privacy/inventory', label: 'DPDP Data Inventory', icon: Cpu },
  { to: '/privacy/consent', label: 'Consent Management', icon: FileBadge }]

},
{
  label: 'Assurance',
  items: [
  { to: '/evidence', label: 'Evidence Repository', icon: FileBadge },
  { to: '/audit-log', label: 'Audit Logs', icon: Activity },
  { to: '/reports', label: 'Reports', icon: FileBarChart }]

},
{
  label: 'System',
  items: [{ to: '/settings', label: 'Settings', icon: Settings }]
}];


export const routeTitles: Record<string, string> = {
  '/': 'Command Center',
  '/copilot': 'Sentinel AI Copilot',
  '/investigations': 'Investigations',
  '/graph': 'Organization Graph',
  '/policies': 'Policies',
  '/controls': 'Compliance Controls',
  '/frameworks': 'Frameworks',
  '/risk': 'Risk Center',
  '/findings': 'Findings',
  '/org/employees': 'Employees',
  '/org/identity': 'Identity & Access',
  '/org/devices': 'Devices',
  '/org/applications': 'Applications',
  '/org/cloud': 'Cloud Assets',
  '/org/vendors': 'Third-Party Vendors',
  '/privacy/inventory': 'DPDP Data Inventory',
  '/privacy/consent': 'Consent Management',
  '/evidence': 'Evidence Repository',
  '/audit-log': 'Audit Logs',
  '/reports': 'Reports',
  '/settings': 'Settings',
  '/profile': 'Profile'
};