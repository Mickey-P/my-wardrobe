import { useEffect, useRef, useState } from 'react'
import { ImageOff } from 'lucide-react'
import { API_BASE, getToken } from './api'

type Props = { id: string; alt?: string; className?: string }

export default function ItemPhoto({ id, alt = id, className = '' }: Props) {
  const [src, setSrc] = useState('')
  const [failed, setFailed] = useState(false)
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    let objectUrl = ''
    let observer: IntersectionObserver | undefined
    const load = async () => {
      try {
        const token = getToken()
        const response = await fetch(`${API_BASE}/api/v1/items/${id}/photo`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!response.ok) throw new Error('No photo')
        objectUrl = URL.createObjectURL(await response.blob())
        if (active) setSrc(objectUrl)
      } catch {
        if (active) setFailed(true)
      }
    }
    if (!host.current || !('IntersectionObserver' in window)) {
      void load()
    } else {
      observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void load()
          observer?.disconnect()
        }
      }, { rootMargin: '180px' })
      observer.observe(host.current)
    }
    return () => {
      active = false
      observer?.disconnect()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [id])

  return (
    <div className={`item-photo ${className}`} ref={host}>
      {src && !failed ? <img src={src} alt={alt} loading="lazy" /> : (
        <div className="photo-placeholder"><ImageOff size={21} /><span>{failed ? 'Фото отсутствует' : 'Загрузка фото'}</span></div>
      )}
    </div>
  )
}
