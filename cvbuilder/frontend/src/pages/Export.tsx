import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { CVInstance } from '../lib/api'
import { Button, Card, PageHeader, Spinner } from '../components/ui'
import { Download, Upload, FileText, AlertCircle, CheckCircle, Files } from 'lucide-react'

export function Export() {
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState<{ ok: boolean; msg: string } | null>(null)
  const cvRef = useRef<HTMLInputElement>(null)
  const refsRef = useRef<HTMLInputElement>(null)

  const { data: cvInstances = [], isLoading: instancesLoading } = useQuery<CVInstance[]>({
    queryKey: ['cv-instances'],
    queryFn: () => api.get('/cv-instances').then(r => r.data),
  })

  async function downloadYaml() {
    const res = await api.get('/export/yaml', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a'); a.href = url; a.download = 'cvbuilder_backup.yml'; a.click()
    URL.revokeObjectURL(url)
  }

  async function downloadInstancePdf(id: number, name: string) {
    try {
      const res = await api.post(`/cv-instances/${id}/export/pdf`, {}, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url; a.download = `${name}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('PDF export failed:', err)
      alert('PDF export failed. Check the browser console for details.')
    }
  }

  async function handleImport() {
    const cvFile = cvRef.current?.files?.[0]
    const refsFile = refsRef.current?.files?.[0]
    if (!cvFile && !refsFile) {
      setImportMsg({ ok: false, msg: 'Please select at least one file to import.' })
      return
    }
    setImporting(true)
    setImportMsg(null)
    try {
      const formData = new FormData()
      if (cvFile) formData.append('cv_file', cvFile)
      if (refsFile) formData.append('refs_file', refsFile)
      const res = await api.post('/export/yaml/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setImportMsg({ ok: true, msg: res.data.imported.join(', ') + ' — import complete.' })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setImportMsg({ ok: false, msg: err.response?.data?.detail || 'Import failed.' })
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="p-8">
      <PageHeader title="Import/Export" subtitle="Download your CV or import existing YAML files" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Download section */}
        <Card className="p-6 space-y-4">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Download size={18} /> Export CV
          </h3>

          <div className="space-y-3">
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">YAML Backup</p>
              <p className="text-xs text-gray-500 mb-3">Export all data as a YAML file for backup or migration.</p>
              <Button variant="secondary" onClick={downloadYaml}>
                <Download size={14} /> Download YAML Backup
              </Button>
            </div>

            {instancesLoading ? <Spinner /> : cvInstances.length > 0 ? (
              <div className="p-4 border border-gray-200 rounded-lg">
                <p className="text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                  <Files size={14} /> PDF Export
                </p>
                <p className="text-xs text-gray-500 mb-3">Generate a PDF from one of your curated CVs.</p>
                <div className="space-y-2">
                  {cvInstances.map(inst => (
                    <div key={inst.id} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText size={14} className="text-gray-400" />
                        <span className="text-sm text-gray-700">{inst.name}</span>
                        <span className="text-xs text-gray-400">({inst.template_name})</span>
                      </div>
                      <Button size="sm" onClick={() => downloadInstancePdf(inst.id, inst.name)}>
                        <Download size={12} /> PDF
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-4">
                No CV instances yet. Create one on the CV Instances page.
              </p>
            )}
          </div>
        </Card>

        {/* Import section */}
        <Card className="p-6 space-y-4">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Upload size={18} /> Import YAML
          </h3>
          <p className="text-sm text-gray-500">
            Import a combined backup file (exported above), or separate{' '}
            <code className="bg-gray-100 px-1 rounded">CV.yml</code> and{' '}
            <code className="bg-gray-100 px-1 rounded">refs.yml</code> files.
            This will replace existing data in the database.
          </p>

          {importMsg && (
            <div className={`flex items-start gap-2 px-4 py-3 rounded-lg text-sm border ${
              importMsg.ok
                ? 'bg-green-50 text-green-800 border-green-200'
                : 'bg-red-50 text-red-800 border-red-200'
            }`}>
              {importMsg.ok ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              {importMsg.msg}
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">CV.yml or combined backup</label>
              <input ref={cvRef} type="file" accept=".yml,.yaml" className="text-sm text-gray-600" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">refs.yml (optional if using combined backup)</label>
              <input ref={refsRef} type="file" accept=".yml,.yaml" className="text-sm text-gray-600" />
            </div>
            <Button onClick={handleImport} loading={importing}>
              <Upload size={14} /> Import Files
            </Button>
          </div>

          <div className="pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-400">
              You can also import from the command line:<br />
              <code className="text-xs bg-gray-100 px-1 rounded">
                python -m app.services.yaml_import --cv mydata/CV.yml --refs mydata/refs.yml
              </code>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}
