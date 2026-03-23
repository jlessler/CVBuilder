import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { Shield, ShieldOff, UserCheck, UserX, Trash2, KeyRound } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { listUsers, updateUser, deleteUser, adminResetPassword, type UserOut } from '../lib/api'
import { Button, Input } from '../components/ui'

export function Users() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [confirmDelete, setConfirmDelete] = useState<UserOut | null>(null)
  const [resetTarget, setResetTarget] = useState<UserOut | null>(null)
  const [resetPw, setResetPw] = useState('')
  const [resetConfirm, setResetConfirm] = useState('')
  const [resetError, setResetError] = useState('')
  const [resetSuccess, setResetSuccess] = useState(false)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: listUsers,
    enabled: !!currentUser?.is_admin,
  })

  const toggleActive = useMutation({
    mutationFn: (u: UserOut) => updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  const toggleAdmin = useMutation({
    mutationFn: (u: UserOut) => updateUser(u.id, { is_admin: !u.is_admin }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  const removeUser = useMutation({
    mutationFn: (userId: number) => deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setConfirmDelete(null)
    },
  })

  const resetPassword = useMutation({
    mutationFn: ({ userId, password }: { userId: number; password: string }) =>
      adminResetPassword(userId, password),
    onSuccess: () => {
      setResetSuccess(true)
      setResetPw('')
      setResetConfirm('')
      setResetError('')
    },
    onError: (err: any) => setResetError(err?.response?.data?.detail || 'Failed to reset password'),
  })

  function openReset(u: UserOut) {
    setResetTarget(u)
    setResetPw('')
    setResetConfirm('')
    setResetError('')
    setResetSuccess(false)
  }

  function closeReset() {
    setResetTarget(null)
    setResetPw('')
    setResetConfirm('')
    setResetError('')
    setResetSuccess(false)
  }

  if (!currentUser?.is_admin) return <Navigate to="/" replace />

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">User Management</h1>

      {isLoading ? (
        <p className="text-gray-500">Loading users...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((u) => {
                const isSelf = u.id === currentUser?.id
                return (
                  <tr key={u.id} className={isSelf ? 'bg-primary-50' : ''}>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {u.full_name || '—'}
                      {isSelf && <span className="ml-2 text-xs text-primary-600">(you)</span>}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {u.is_admin && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          Admin
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {!isSelf && (
                          <>
                            <button
                              onClick={() => toggleActive.mutate(u)}
                              disabled={toggleActive.isPending}
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                              title={u.is_active ? 'Deactivate' : 'Activate'}
                            >
                              {u.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                            </button>
                            <button
                              onClick={() => toggleAdmin.mutate(u)}
                              disabled={toggleAdmin.isPending}
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                              title={u.is_admin ? 'Remove admin' : 'Make admin'}
                            >
                              {u.is_admin ? <ShieldOff size={16} /> : <Shield size={16} />}
                            </button>
                            <button
                              onClick={() => openReset(u)}
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                              title="Reset password"
                            >
                              <KeyRound size={16} />
                            </button>
                            <button
                              onClick={() => setConfirmDelete(u)}
                              className="p-1.5 rounded hover:bg-red-50 text-gray-500 hover:text-red-600"
                              title="Delete user"
                            >
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete User</h3>
            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to delete <strong>{confirmDelete.email}</strong>?
              This will permanently remove the user and all their CV data.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" size="sm" onClick={() => setConfirmDelete(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                loading={removeUser.isPending}
                onClick={() => removeUser.mutate(confirmDelete.id)}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Reset password dialog */}
      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4 space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">Reset Password</h3>
            <p className="text-sm text-gray-600">
              Set a new password for <strong>{resetTarget.email}</strong>.
            </p>
            {resetSuccess && (
              <div className="px-3 py-2 bg-green-50 text-green-800 rounded text-sm border border-green-200">
                Password reset successfully.
              </div>
            )}
            {resetError && (
              <div className="px-3 py-2 bg-red-50 text-red-800 rounded text-sm border border-red-200">
                {resetError}
              </div>
            )}
            {!resetSuccess && (
              <>
                <Input label="New Password" type="password" value={resetPw} onChange={e => setResetPw(e.target.value)} />
                {resetPw && resetPw.length < 6 && <p className="text-xs text-red-500">Password must be at least 6 characters</p>}
                <Input label="Confirm Password" type="password" value={resetConfirm} onChange={e => setResetConfirm(e.target.value)} />
                {resetConfirm && resetPw !== resetConfirm && <p className="text-xs text-red-500">Passwords do not match</p>}
              </>
            )}
            <div className="flex justify-end gap-3">
              <Button variant="secondary" size="sm" onClick={closeReset}>
                {resetSuccess ? 'Close' : 'Cancel'}
              </Button>
              {!resetSuccess && (
                <Button
                  size="sm"
                  loading={resetPassword.isPending}
                  disabled={!resetPw || resetPw.length < 6 || resetPw !== resetConfirm}
                  onClick={() => resetPassword.mutate({ userId: resetTarget.id, password: resetPw })}
                >
                  Reset Password
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
