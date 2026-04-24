import { AdminDocumentDetailView } from "@/components/admin/admin-document-detail";

export default function AdminDocumentPage({ params }: { params: { documentId: string } }) {
  return <AdminDocumentDetailView documentId={Number(params.documentId)} />;
}
