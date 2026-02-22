import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Profile as ProfileType } from '../lib/api'
import { Button, Card, Input, PageHeader, Spinner } from '../components/ui'
import { Plus, Trash2 } from 'lucide-react'

export function Profile() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<ProfileType>({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then(r => r.data).catch(() => null),
    retry: false,
  })

  const [form, setForm] = useState({
    name: '', email: '', phone: '', website: '', orcid: '', linkedin: '',
    homeAddr: [''], workAddr: [''],
  })

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name || '',
        email: data.email || '',
        phone: data.phone || '',
        website: data.website || '',
        orcid: data.orcid || '',
        linkedin: data.linkedin || '',
        homeAddr: data.addresses.filter(a => a.type === 'home').sort((a, b) => a.line_order - b.line_order).map(a => a.text),
        workAddr: data.addresses.filter(a => a.type === 'work').sort((a, b) => a.line_order - b.line_order).map(a => a.text),
      })
    }
  }, [data])

  const save = useMutation({
    mutationFn: () => {
      const addresses = [
        ...form.homeAddr.filter(Boolean).map((text, i) => ({ type: 'home', line_order: i, text })),
        ...form.workAddr.filter(Boolean).map((text, i) => ({ type: 'work', line_order: i, text })),
      ]
      return api.put('/profile', {
        name: form.name, email: form.email, phone: form.phone,
        website: form.website, orcid: form.orcid, linkedin: form.linkedin,
        addresses,
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }))
  }

  function setAddr(type: 'homeAddr' | 'workAddr', idx: number, val: string) {
    setForm(f => ({ ...f, [type]: f[type].map((v, i) => i === idx ? val : v) }))
  }

  function addAddr(type: 'homeAddr' | 'workAddr') {
    setForm(f => ({ ...f, [type]: [...f[type], ''] }))
  }

  function removeAddr(type: 'homeAddr' | 'workAddr', idx: number) {
    setForm(f => ({ ...f, [type]: f[type].filter((_, i) => i !== idx) }))
  }

  return (
    <div className="p-8">
      <PageHeader
        title="Profile"
        subtitle="Your personal and contact information"
        actions={
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            Save Changes
          </Button>
        }
      />

      {save.isSuccess && (
        <div className="mb-4 px-4 py-2 bg-green-50 text-green-800 rounded-lg text-sm border border-green-200">
          Saved successfully.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <h3 className="font-semibold text-gray-900">Personal Information</h3>
          <Input label="Full Name" value={form.name} onChange={e => set('name', e.target.value)} />
          <Input label="Email" type="email" value={form.email} onChange={e => set('email', e.target.value)} />
          <Input label="Phone" value={form.phone} onChange={e => set('phone', e.target.value)} />
          <Input label="Website / Homepage" value={form.website} onChange={e => set('website', e.target.value)} />
          <Input label="ORCID" placeholder="0000-0000-0000-0000" value={form.orcid} onChange={e => set('orcid', e.target.value)} />
          <Input label="LinkedIn" value={form.linkedin} onChange={e => set('linkedin', e.target.value)} />
        </Card>

        <div className="space-y-6">
          <Card className="p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Work Address</h3>
              <Button variant="ghost" size="sm" onClick={() => addAddr('workAddr')}>
                <Plus size={14} /> Add line
              </Button>
            </div>
            {form.workAddr.map((line, i) => (
              <div key={i} className="flex gap-2">
                <Input value={line} onChange={e => setAddr('workAddr', i, e.target.value)} className="flex-1" />
                <button className="text-red-400 hover:text-red-600 mt-0" onClick={() => removeAddr('workAddr', i)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </Card>

          <Card className="p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Home Address</h3>
              <Button variant="ghost" size="sm" onClick={() => addAddr('homeAddr')}>
                <Plus size={14} /> Add line
              </Button>
            </div>
            {form.homeAddr.map((line, i) => (
              <div key={i} className="flex gap-2">
                <Input value={line} onChange={e => setAddr('homeAddr', i, e.target.value)} className="flex-1" />
                <button className="text-red-400 hover:text-red-600" onClick={() => removeAddr('homeAddr', i)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  )
}
