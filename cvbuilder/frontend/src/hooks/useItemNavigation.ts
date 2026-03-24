import { useState, useMemo, useCallback, useEffect, useRef } from 'react'

interface NavigableItem {
  id: number
  [key: string]: unknown
}

interface UseItemNavigationOptions<T extends NavigableItem> {
  items: T[]
  currentId: number | null
  onSave: () => Promise<void>
  onNavigate: (item: T, index: number) => void
  wrapAround?: boolean
}

interface UseItemNavigationResult {
  currentIndex: number
  total: number
  canPrev: boolean
  canNext: boolean
  goPrev: () => Promise<void>
  goNext: () => Promise<void>
  isSaving: boolean
  saveError: string | null
  dirtyRef: React.MutableRefObject<boolean>
}

export function useItemNavigation<T extends NavigableItem>({
  items,
  currentId,
  onSave,
  onNavigate,
  wrapAround = false,
}: UseItemNavigationOptions<T>): UseItemNavigationResult {
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const dirtyRef = useRef(false)

  // Use refs to always get latest callbacks — avoids stale closure issues
  const onSaveRef = useRef(onSave)
  onSaveRef.current = onSave
  const onNavigateRef = useRef(onNavigate)
  onNavigateRef.current = onNavigate
  const itemsRef = useRef(items)
  itemsRef.current = items

  const currentIndex = useMemo(() => {
    if (currentId === null) return -1
    return items.findIndex(item => item.id === currentId)
  }, [items, currentId])

  const total = items.length
  const canPrev = currentIndex > 0 || (wrapAround && total > 1)
  const canNext = currentIndex < total - 1 || (wrapAround && total > 1)

  // Use a ref for isSaving to prevent double-clicks without stale closure issues
  const isSavingRef = useRef(false)

  const navigate = useCallback(async (direction: 'prev' | 'next') => {
    if (isSavingRef.current) return
    const idx = itemsRef.current.findIndex(item => item.id === currentId)
    if (idx < 0) return
    const len = itemsRef.current.length

    let newIndex: number
    if (direction === 'next') {
      newIndex = idx + 1
      if (newIndex >= len) {
        if (wrapAround) newIndex = 0
        else return
      }
    } else {
      newIndex = idx - 1
      if (newIndex < 0) {
        if (wrapAround) newIndex = len - 1
        else return
      }
    }

    isSavingRef.current = true
    setIsSaving(true)
    setSaveError(null)
    try {
      await onSaveRef.current()
      dirtyRef.current = true
      onNavigateRef.current(itemsRef.current[newIndex], newIndex)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      isSavingRef.current = false
      setIsSaving(false)
    }
  }, [currentId, wrapAround])

  const goNext = useCallback(() => navigate('next'), [navigate])
  const goPrev = useCallback(() => navigate('prev'), [navigate])

  // Reset dirty flag when modal closes
  useEffect(() => {
    if (currentId === null) {
      dirtyRef.current = false
    }
  }, [currentId])

  // Keyboard shortcuts
  useEffect(() => {
    if (currentId === null) return

    function handleKeyDown(e: KeyboardEvent) {
      const el = e.target as HTMLElement
      const tag = el?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (el?.isContentEditable) return

      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        navigate('prev')
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        navigate('next')
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [currentId, navigate])

  return {
    currentIndex,
    total,
    canPrev,
    canNext,
    goPrev,
    goNext,
    isSaving,
    saveError,
    dirtyRef,
  }
}
