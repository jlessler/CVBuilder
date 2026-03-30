import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, changePassword } from '../lib/api'
import type { Profile as ProfileType } from '../lib/api'
import { Button, Card, Input, PageHeader, Spinner } from '../components/ui'
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react'

const PARTICLES = new Set(['van','von','de','del','della','di','du','des','der','den','la','le','el','al','bin','ibn','ben','st','st.','mac','mc'])
const SUFFIXES = new Set(['jr','jr.','sr','sr.','ii','iii','iv','v','phd','md'])

function isInitials(t: string) { const c = t.replace(/\./g,''); return c.length>0 && c.length<=3 && /^[A-Z]+$/.test(c) }
function splitInit(t: string): [string, string|null] { const c=t.replace(/\./g,''); return c.length===1?[c,null]:[c[0],c.slice(1)] }

function parseProfileName(name: string) {
  const r = { given_name:'', family_name:'', suffix:'' }
  if (!name?.trim()) return r
  const s = name.trim().replace(/\s+/g,' ')
  const makeGiven = (first: string, mid: string|null) => mid ? `${first} ${mid}` : first
  const extractSuffix = (ts: string[]): [string[],string] => {
    if (ts.length>0 && SUFFIXES.has(ts[ts.length-1].replace(/[.,]/g,'').toLowerCase())) return [ts.slice(0,-1), ts[ts.length-1].replace(/,/,'')]
    return [ts,'']
  }
  if (s.includes(',')) {
    const [fam,...rest] = s.split(',').map(p=>p.trim())
    let gp = rest[0]||''
    if (SUFFIXES.has(gp.replace(/[.,]/g,'').toLowerCase())) { r.suffix=gp.replace(/,/,''); gp=rest[1]?.trim()||'' }
    const ft=fam.split(' ')
    if (ft.length>1 && SUFFIXES.has(ft[ft.length-1].replace(/[.,]/g,'').toLowerCase())) { r.suffix=ft[ft.length-1].replace(/,/,''); r.family_name=ft.slice(0,-1).join(' ') } else r.family_name=fam
    const gt=gp?gp.split(' '):[]
    if (gt.length===1) { const t=gt[0].replace(/\.$/,''); if(isInitials(t)){const[f,m]=splitInit(t);r.given_name=makeGiven(f+'.',m?[...m].join('.')+'.':null)} else r.given_name=gt[0] }
    else if (gt.length>1) { r.given_name=gt.join(' ') }
    return r
  }
  let tokens=s.split(' '); let sfx=''; [tokens,sfx]=extractSuffix(tokens); r.suffix=sfx
  if (tokens.length<=1) { r.family_name=tokens[0]||''; return r }
  if (tokens.length===2) {
    if (isInitials(tokens[1])){r.family_name=tokens[0];const[f,m]=splitInit(tokens[1]);r.given_name=makeGiven(f+'.',m?[...m].join('.')+'.':null)}
    else if(isInitials(tokens[0])){const[f,m]=splitInit(tokens[0]);r.given_name=makeGiven(f+'.',m?[...m].join('.')+'.':null);r.family_name=tokens[1]}
    else{r.given_name=tokens[0];r.family_name=tokens[1]}
    return r
  }
  const first=tokens[0]
  let fs=tokens.length-1; while(fs>1&&PARTICLES.has(tokens[fs-1].toLowerCase().replace(/,/,'')))fs--
  r.family_name=tokens.slice(fs).join(' '); const mt=tokens.slice(1,fs)
  r.given_name=mt.length?makeGiven(first,mt.join(' ')):first
  return r
}

function composeProfileName(given: string, family: string, suffix: string) {
  if (!family && !given) return ''
  const parts = [given, family].filter(Boolean)
  let name = parts.join(' ')
  if (suffix) name += ' ' + suffix
  return name
}

export function Profile() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<ProfileType>({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then(r => r.data).catch(() => null),
    retry: false,
  })

  const [form, setForm] = useState({
    name: '', email: '', phone: '', website: '', orcid: '', semantic_scholar_id: '', linkedin: '',
    given_name: '', family_name: '', suffix: '',
    homeAddr: [''], workAddr: [''],
  })
  const [showNameParts, setShowNameParts] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name || '',
        email: data.email || '',
        phone: data.phone || '',
        website: data.website || '',
        orcid: data.orcid || '',
        semantic_scholar_id: data.semantic_scholar_id || '',
        linkedin: data.linkedin || '',
        given_name: data.given_name || '',
        family_name: data.family_name || '',
        suffix: data.suffix || '',
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
        website: form.website, orcid: form.orcid,
        semantic_scholar_id: form.semantic_scholar_id,
        linkedin: form.linkedin,
        given_name: form.given_name || null,
        family_name: form.family_name || null,
        suffix: form.suffix || null,
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
          <Input label="Full Name" value={form.name}
            onChange={e => set('name', e.target.value)}
            onBlur={() => setForm(f => ({ ...f, ...parseProfileName(f.name) }))}
          />
          <button
            type="button"
            onClick={() => setShowNameParts(!showNameParts)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 -mt-2"
          >
            {showNameParts ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            Name parts (for citation formatting)
          </button>
          {showNameParts && (
            <div className="grid grid-cols-3 gap-2 -mt-2">
              <Input label="Given" value={form.given_name} onChange={e => setForm(f => ({ ...f, given_name: e.target.value, name: composeProfileName(e.target.value, f.family_name, f.suffix) }))} />
              <Input label="Family" value={form.family_name} onChange={e => setForm(f => ({ ...f, family_name: e.target.value, name: composeProfileName(f.given_name, e.target.value, f.suffix) }))} />
              <Input label="Suffix" value={form.suffix} onChange={e => setForm(f => ({ ...f, suffix: e.target.value, name: composeProfileName(f.given_name, f.family_name, e.target.value) }))} />
            </div>
          )}
          <Input label="Email" type="email" value={form.email} onChange={e => set('email', e.target.value)} />
          <Input label="Phone" value={form.phone} onChange={e => set('phone', e.target.value)} />
          <Input label="Website / Homepage" value={form.website} onChange={e => set('website', e.target.value)} />
          <Input label="ORCID" placeholder="0000-0000-0000-0000" value={form.orcid} onChange={e => set('orcid', e.target.value)} />
          <Input label="Semantic Scholar Author ID" placeholder="e.g. 1741101" value={form.semantic_scholar_id} onChange={e => set('semantic_scholar_id', e.target.value)} />
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

          <ChangePasswordCard />
        </div>
      </div>
    </div>
  )
}

function ChangePasswordCard() {
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [error, setError] = useState('')

  const mut = useMutation({
    mutationFn: () => changePassword(currentPw, newPw),
    onSuccess: () => { setCurrentPw(''); setNewPw(''); setConfirmPw(''); setError('') },
    onError: (err: any) => setError(err?.response?.data?.detail || 'Failed to change password'),
  })

  const mismatch = confirmPw !== '' && newPw !== confirmPw
  const tooShort = newPw !== '' && newPw.length < 6
  const canSubmit = currentPw && newPw && confirmPw && !mismatch && !tooShort

  return (
    <Card className="p-6 space-y-3">
      <h3 className="font-semibold text-gray-900">Change Password</h3>
      {mut.isSuccess && (
        <div className="px-3 py-2 bg-green-50 text-green-800 rounded text-sm border border-green-200">
          Password updated successfully.
        </div>
      )}
      {error && (
        <div className="px-3 py-2 bg-red-50 text-red-800 rounded text-sm border border-red-200">
          {error}
        </div>
      )}
      <Input label="Current Password" type="password" value={currentPw} onChange={e => { setCurrentPw(e.target.value); setError('') }} />
      <Input label="New Password" type="password" value={newPw} onChange={e => setNewPw(e.target.value)} />
      {tooShort && <p className="text-xs text-red-500">Password must be at least 6 characters</p>}
      <Input label="Confirm New Password" type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} />
      {mismatch && <p className="text-xs text-red-500">Passwords do not match</p>}
      <div className="flex justify-end">
        <Button onClick={() => mut.mutate()} loading={mut.isPending} disabled={!canSubmit}>
          Update Password
        </Button>
      </div>
    </Card>
  )
}
