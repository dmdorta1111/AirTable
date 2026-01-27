import { AuditLogViewer } from "@/components/audit/AuditLogViewer"

export default function AuditLogPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Logs</h1>
        <p className="text-muted-foreground">
          View and search tamper-evident audit trail for compliance
        </p>
      </div>
      <AuditLogViewer />
    </div>
  )
}
