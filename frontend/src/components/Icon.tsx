const paths: Record<string, string> = {
  dashboard: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  incidents: 'M6 3h12v18H6z M9 7h6 M9 11h6 M9 15h4',
  departments: 'M3 21h18 M5 21V8h14v13 M3 8l9-5 9 5 M9 11v6 M15 11v6',
  history: 'M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l3 2',
  critical: 'M12 3 2 21h20L12 3z M12 9v5 M12 17v1',
  search: 'M20 20l-5-5 M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
  arrow: 'M5 12h14 M14 7l5 5-5 5',
  settings: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
};
export default function Icon({ name }: { name: string }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name] ?? paths.incidents} /></svg>;
}
