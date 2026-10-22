import { useState } from 'react'
import {
  Copy,
  Download,
  Eye,
  FileCheck,
  FileCode,
  FileSpreadsheet,
  Printer,
  RotateCw,
  ShieldCheck,
} from 'lucide-react'
import { useReport } from '../api/queries'
import { PageHeader } from '../components/common/PageHeader'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { EmptyState } from '../components/ui/empty-state'
import { ErrorState } from '../components/ui/error-state'
import { Skeleton } from '../components/ui/skeleton'
import { useRunContext } from '../context/RunContext'

export function ReportsPage() {
  const { selectedRunId } = useRunContext()
  const { data: report, isLoading, error, refetch } = useReport(selectedRunId)

  const [activeTab, setActiveTab] = useState<'rendered' | 'raw'>('rendered')
  const [copied, setCopied] = useState(false)

  const handleDownloadMarkdown = () => {
    if (!report?.markdown_content) return
    const blob = new Blob([report.markdown_content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SafeSpec_Verification_Report_${selectedRunId || 'cycle'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    if (!report?.markdown_content) return
    navigator.clipboard.writeText(report.markdown_content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePrint = () => {
    window.print()
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Compliance Reports"
          subtitle="Audit documentation."
        />
        <ErrorState
          title="Failed to load verification report"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance Reports"
        subtitle="Audit and compliance certification reports generated from formal proofs and test results."
        badge={report ? 'Audit Ready' : undefined}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="gap-1.5 border-[#202F2B] bg-[#141D1B] text-[#94A3B8] hover:bg-[#1A2623] hover:text-[#F8FAFC]"
            >
              <RotateCw className="h-3.5 w-3.5" />
              <span>Regenerate</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handlePrint}
              disabled={!report}
              className="gap-1.5 border-[#263632] bg-[#182421] text-[#A8B5B1] hover:bg-[#202E2A] hover:text-[#F5F7F6]"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Print</span>
            </Button>

            <Button
              variant="accent"
              size="sm"
              onClick={handleDownloadMarkdown}
              disabled={!report?.markdown_content}
              className="gap-1.5 font-bold"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download<span className="hidden sm:inline"> Markdown</span></span>
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full bg-[#182421]" />
          <Skeleton className="h-96 w-full bg-[#182421]" />
        </div>
      ) : !report ? (
        <EmptyState
          icon={FileSpreadsheet}
          title="No Compliance Report Generated Yet"
          description="Start a verification workflow on the Upload page to compile formal proofs, test logs, and automotive audit records."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Metadata Rail */}
          <div className="space-y-4">
            <Card className="border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C]">
              <CardHeader className="border-b border-[#263632] pb-3">
                <CardTitle className="text-sm flex items-center gap-2 text-[#F5F7F6]">
                  <ShieldCheck className="h-4 w-4 text-[#19C997]" />
                  <span>Report Summary</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 font-mono text-xs p-4">
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#71807B] block font-sans">
                    Verification Cycle
                  </span>
                  <span className="font-bold text-[#F4C430] text-sm">
                    {report.run_id}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-bold text-[#71807B] block font-sans">
                    Generation Timestamp
                  </span>
                  <span className="text-[#A8B5B1]">
                    {new Date(report.generated_at).toLocaleString()}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-bold text-[#71807B] block font-sans mb-1">
                    Compliance Standard
                  </span>
                  <Badge variant="success" className="text-[10px]">
                    ISO 26262 ASIL D
                  </Badge>
                </div>

                <div className="pt-2 border-t border-[#263632]">
                  <span className="text-[10px] uppercase font-bold text-[#71807B] block font-sans">
                    Local Markdown File
                  </span>
                  <span className="text-[11px] font-mono text-[#71807B] truncate block">
                    {report.markdown_path}
                  </span>
                </div>

                {report.pdf_path && (
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#71807B] block font-sans">
                      Compiled PDF Document
                    </span>
                    <span className="text-[11px] font-mono text-[#71807B] truncate block">
                      {report.pdf_path}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C]">
              <CardContent className="p-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="w-full gap-2 text-xs border-[#263632] bg-[#182421] text-[#A8B5B1] hover:bg-[#202E2A] hover:text-[#F5F7F6]"
                >
                  <Copy className="h-3.5 w-3.5 text-[#F4C430]" />
                  <span>{copied ? 'Copied to Clipboard!' : 'Copy Markdown Text'}</span>
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Main Document Viewer */}
          <Card className="lg:col-span-3 overflow-hidden flex flex-col border-[#263632] bg-gradient-to-b from-[#162320] to-[#141E1C]">
            <CardHeader className="flex flex-row items-center justify-between border-b border-[#263632] pb-3">
              <div className="flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-[#F4C430]" />
                <CardTitle className="text-sm text-[#F5F7F6]">
                  SafeSpec Safety Verification Document
                </CardTitle>
              </div>

              {/* View Mode Tabs */}
              <div className="flex items-center rounded-md border border-[#263632] bg-[#0B1110] p-1 text-xs">
                <button
                  onClick={() => setActiveTab('rendered')}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-semibold transition ${
                    activeTab === 'rendered'
                      ? 'bg-[#182421] text-[#F4C430] border border-[#F4C430]/30 shadow-xs'
                      : 'text-[#71807B] hover:text-[#F5F7F6]'
                  }`}
                >
                  <Eye className="h-3 w-3" />
                  <span>Formatted View</span>
                </button>
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-semibold transition ${
                    activeTab === 'raw'
                      ? 'bg-[#182421] text-[#F4C430] border border-[#F4C430]/30 shadow-xs'
                      : 'text-[#71807B] hover:text-[#F5F7F6]'
                  }`}
                >
                  <FileCode className="h-3 w-3" />
                  <span>Raw Markdown</span>
                </button>
              </div>
            </CardHeader>

            <CardContent className="p-6 flex-1 overflow-y-auto">
              {activeTab === 'rendered' ? (
                <div className="space-y-4 text-xs font-sans text-[#F5F7F6] leading-relaxed">
                  {/* Clean Formatted Sections */}
                  {report.markdown_content.split('\n\n').map((paragraph, idx) => {
                    if (paragraph.startsWith('# ')) {
                      return (
                        <h1
                          key={idx}
                          className="font-display text-xl font-bold tracking-tight text-[#F5F7F6] border-b border-[#263632] pb-2 pt-2"
                        >
                          {paragraph.replace('# ', '')}
                        </h1>
                      )
                    }
                    if (paragraph.startsWith('## ')) {
                      return (
                        <h2
                          key={idx}
                          className="font-display text-base font-bold text-[#F4C430] border-b border-[#263632]/70 pb-1 pt-3"
                        >
                          {paragraph.replace('## ', '')}
                        </h2>
                      )
                    }
                    if (paragraph.startsWith('### ')) {
                      return (
                        <h3
                          key={idx}
                          className="font-display text-xs font-bold text-[#00B8D9] uppercase tracking-wider pt-2"
                        >
                          {paragraph.replace('### ', '')}
                        </h3>
                      )
                    }
                    if (paragraph.startsWith('- ') || paragraph.startsWith('* ')) {
                      return (
                        <ul
                          key={idx}
                          className="list-inside list-disc space-y-1 pl-2 text-[#A8B5B1]"
                        >
                          {paragraph.split('\n').map((line, liIdx) => (
                            <li key={liIdx}>
                              {line.replace(/^[-*]\s+/, '')}
                            </li>
                          ))}
                        </ul>
                      )
                    }
                    if (paragraph.startsWith('```')) {
                      return (
                        <pre
                          key={idx}
                          className="rounded-md border border-[#263632] bg-[#0B1110] p-3 font-mono text-[11px] text-[#19C997] overflow-x-auto shadow-inner leading-relaxed"
                        >
                          {paragraph.replace(/```[a-z]*\n?/g, '')}
                        </pre>
                      )
                    }
                    return (
                      <p key={idx} className="text-[#A8B5B1] leading-relaxed">
                        {paragraph}
                      </p>
                    )
                  })}
                </div>
              ) : (
                <pre className="rounded-md border border-[#263632] bg-[#0B1110] p-4 font-mono text-[11px] text-[#A8B5B1] overflow-x-auto leading-relaxed shadow-inner">
                  {report.markdown_content}
                </pre>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
