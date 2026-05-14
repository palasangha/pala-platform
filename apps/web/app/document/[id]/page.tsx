import DocumentHitViewer from '@/components/DocumentHitViewer';

type DocumentPageProps = {
  params: { id: string };
  searchParams?: Record<string, string | string[] | undefined>;
};

function firstQueryValue(value: string | string[] | undefined) {
  if (Array.isArray(value)) return value[0] || '';
  return value || '';
}

export default function DocumentPage({ params, searchParams }: DocumentPageProps) {
  const query = firstQueryValue(searchParams?.q);
  const hit = firstQueryValue(searchParams?.hit);

  return <DocumentHitViewer documentId={params.id} initialQuery={query} initialHit={hit} />;
}