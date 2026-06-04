import { useEffect, useState } from 'react'

type Kind = 'error' | 'ok'
interface ToastItem { id: number; msg: string; kind: Kind }

let items: ToastItem[] = []
let listeners: Array<(t: ToastItem[]) => void> = []
let nextId = 1

function emit() { listeners.forEach((l) => l([...items])) }

export function toast(msg: string, kind: Kind = 'error') {
  const id = nextId++
  items = [...items, { id, msg, kind }]
  emit()
  setTimeout(() => { items = items.filter((t) => t.id !== id); emit() }, 4500)
}

export function Toasts() {
  const [list, setList] = useState<ToastItem[]>([])
  useEffect(() => {
    listeners.push(setList)
    return () => { listeners = listeners.filter((l) => l !== setList) }
  }, [])
  return (
    <div className="toasts" aria-live="polite" aria-atomic="false">
      {list.map((t) => <div key={t.id} className={`toast ${t.kind}`} role={t.kind === 'error' ? 'alert' : undefined}>{t.msg}</div>)}
    </div>
  )
}
