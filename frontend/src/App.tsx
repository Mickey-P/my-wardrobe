import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowDownUp, Check, ChevronDown, CircleHelp, Cloud, Download, Grid2X2, Heart,
  Image as ImageIcon, Layers3, ListFilter, LoaderCircle, LockKeyhole, Plus, Search, Upload,
  Pencil, Shirt, SlidersHorizontal, Sparkles, X,
} from 'lucide-react'
import ItemPhoto from './ItemPhoto'
import { api, getToken, TOKEN_KEY } from './api'

type Visual = { visual_description?: string; critical_details?: string; uncertainties?: string }
type WardrobeItem = {
  id: string
  catalog_fields: Record<string, string>
  user_notes: string
  visual_description: Visual | null
  local_image_path: string | null
  image_status: string
}
type Stats = {
  total_items: number
  by_category: Record<string, number>
  by_season: Record<string, number>
  by_status: Record<string, number>
  with_photos: number
  without_photos: number
}
type Outfit = { id: number; name: string; description: string; season: string; occasion: string; item_ids: string[] }
type Page = 'overview' | 'items' | 'photos' | 'outfits'
type Filters = { category: string; subcategory: string; color: string; season: string; formality: string; warmth: string; fit: string; brand: string; status: string; has_photo: string }

const blankStats: Stats = { total_items: 0, by_category: {}, by_season: {}, by_status: {}, with_photos: 0, without_photos: 0 }
const categoryLabels: Record<string, string> = {
  top: 'Tops', bottom: 'Bottoms', outerwear: 'Outerwear', footwear: 'Footwear', accessory: 'Accessories',
}
const labels: Record<string, string> = {
  subcategory: 'Subcategory', brand: 'Brand', primary_color: 'Primary color', secondary_colors: 'Secondary colors',
  pattern: 'Pattern', fit: 'Fit', material: 'Material', season: 'Season', formality: 'Formality',
  warmth: 'Warmth', status: 'Status', notes: 'Catalog note', filename: 'Source filename',
  ask_clothes_id: 'Ask Clothes ID', clothes_id: 'Clothes ID', image_url: 'Source URL',
}

function display(value?: string) { return value?.trim() || 'Not specified' }
function titleCase(value: string) { return value ? value[0].toUpperCase() + value.slice(1) : value }

export default function App() {
  const [page, setPage] = useState<Page>('overview')
  const [items, setItems] = useState<WardrobeItem[]>([])
  const [outfits, setOutfits] = useState<Outfit[]>([])
  const [stats, setStats] = useState<Stats>(blankStats)
  const [selected, setSelected] = useState<WardrobeItem | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [token, setToken] = useState(getToken)
  const [tokenDraft, setTokenDraft] = useState(token)
  const [showSettings, setShowSettings] = useState(false)
  const [tokenVersion, setTokenVersion] = useState(0)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<Filters>({ category: '', subcategory: '', color: '', season: '', formality: '', warmth: '', fit: '', brand: '', status: '', has_photo: '' })
  const [sort, setSort] = useState('id')
  const [composer, setComposer] = useState(false)
  const [editingOutfit, setEditingOutfit] = useState<number | null>(null)
  const [outfitDraft, setOutfitDraft] = useState({ name: '', description: '', season: '', occasion: '', item_ids: [] as string[] })
  const [outfitSearch, setOutfitSearch] = useState('')
  const importInput = useRef<HTMLInputElement>(null)

  const loadData = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      const [nextItems, nextStats, nextOutfits] = await Promise.all([
        api<WardrobeItem[]>('/api/v1/items?limit=500&sort=id'),
        api<Stats>('/api/v1/stats'),
        api<Outfit[]>('/api/v1/outfits'),
      ])
      setItems(nextItems)
      setStats(nextStats)
      setOutfits(nextOutfits)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to load data')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  const filteredItems = useMemo(() => {
    const q = search.trim().toLocaleLowerCase()
    return items.filter((item) => {
      const fields = item.catalog_fields
      const text = [item.id, ...Object.values(fields), item.user_notes, item.visual_description?.visual_description,
        item.visual_description?.critical_details, item.visual_description?.uncertainties].join(' ').toLocaleLowerCase()
      if (q && !text.includes(q)) return false
      if (filters.category && fields.category !== filters.category) return false
      if (filters.subcategory && !String(fields.subcategory || '').toLowerCase().includes(filters.subcategory.toLowerCase())) return false
      if (filters.color && !`${fields.primary_color || ''} ${fields.secondary_colors || ''}`.toLowerCase().includes(filters.color.toLowerCase())) return false
      if (filters.season && !String(fields.season || '').toLowerCase().includes(filters.season.toLowerCase())) return false
      if (filters.formality && !String(fields.formality || '').toLowerCase().includes(filters.formality.toLowerCase())) return false
      if (filters.warmth && !String(fields.warmth || '').toLowerCase().includes(filters.warmth.toLowerCase())) return false
      if (filters.fit && !String(fields.fit || '').toLowerCase().includes(filters.fit.toLowerCase())) return false
      if (filters.brand && !String(fields.brand || '').toLowerCase().includes(filters.brand.toLowerCase())) return false
      if (filters.status && !String(fields.status || '').toLowerCase().includes(filters.status.toLowerCase())) return false
      if (filters.has_photo === 'yes' && !['downloaded', 'already_exists', 'manual_upload'].includes(item.image_status)) return false
      if (filters.has_photo === 'no' && ['downloaded', 'already_exists', 'manual_upload'].includes(item.image_status)) return false
      return true
    }).sort((a, b) => {
      const av = sort === 'id' ? a.id : sort === 'category' ? a.catalog_fields.category : sort === 'color' ? a.catalog_fields.primary_color : a.catalog_fields.brand
      const bv = sort === 'id' ? b.id : sort === 'category' ? b.catalog_fields.category : sort === 'color' ? b.catalog_fields.primary_color : b.catalog_fields.brand
      return String(av || '').localeCompare(String(bv || ''), 'en', { numeric: true })
    })
  }, [items, search, filters, sort])

  const pickToken = () => {
    localStorage.setItem(TOKEN_KEY, tokenDraft.trim())
    setToken(tokenDraft.trim())
    setTokenVersion((value) => value + 1)
    setShowSettings(false)
    void loadData()
  }

  const openComposer = (outfit?: Outfit) => {
    setEditingOutfit(outfit?.id ?? null)
    setOutfitDraft(outfit ? {
      name: outfit.name, description: outfit.description || '', season: outfit.season || '',
      occasion: outfit.occasion || '', item_ids: [...outfit.item_ids],
    } : { name: '', description: '', season: '', occasion: '', item_ids: [] })
    setOutfitSearch('')
    setComposer(true)
  }

  const saveOutfit = async () => {
    if (!outfitDraft.name.trim()) { setError('Enter an outfit name'); return }
    setBusy(true)
    try {
      const path = editingOutfit ? `/api/v1/outfits/${editingOutfit}` : '/api/v1/outfits'
      await api(path, { method: editingOutfit ? 'PUT' : 'POST', body: JSON.stringify(outfitDraft) })
      setComposer(false)
      await loadData()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to save outfit')
    } finally { setBusy(false) }
  }

  const saveItem = async (itemId: string, catalogFields: Record<string, string>, userNotes: string) => {
    try {
      const updated = await api<WardrobeItem>(`/api/v1/items/${itemId}`, {
        method: 'PUT', body: JSON.stringify({ catalog_fields: { ...catalogFields, id: itemId }, user_notes: userNotes }),
      })
      setItems((current) => current.map((item) => item.id === itemId ? updated : item))
      setSelected(updated)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Failed to save item')
      throw reason
    }
  }

  const deleteOutfit = async (id: number) => {
    if (!window.confirm('Delete this outfit?')) return
    try { await api(`/api/v1/outfits/${id}`, { method: 'DELETE' }); await loadData() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Failed to delete outfit') }
  }

  const uploadPhoto = async (item: WardrobeItem, file?: File) => {
    if (!file) return
    const has = ['downloaded', 'already_exists', 'manual_upload'].includes(item.image_status)
    const replace = has && window.confirm(`${item.id} already has a photo. Replace it? The previous file will be saved in the backups folder.`)
    if (has && !replace) return
    const form = new FormData()
    form.append('file', file)
    try {
      await api(`/api/v1/items/${item.id}/photo${replace ? '?replace=true' : ''}`, { method: 'POST', body: form })
      await loadData()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Failed to upload photo') }
  }

  const exportData = async (format: 'zip' | 'catalog.csv' | 'catalog.json') => {
    setError('')
    try {
      const headers = new Headers()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
      const response = await fetch(`${base}/api/v1/exports/${format}`, { headers })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(typeof body?.detail === 'string' ? body.detail : `Export failed (${response.status})`)
      }
      const objectUrl = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = format === 'zip' ? `wardrobe_export_${new Date().toISOString().slice(0, 10)}.zip` : format
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Failed to export data') }
  }

  const importArchive = async (file?: File) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.zip')) { setError('Select a wardrobe ZIP export'); return }
    const submit = async (overwrite: boolean) => {
      const form = new FormData()
      form.append('file', file)
      const headers = new Headers()
      if (token) headers.set('Authorization', `Bearer ${token}`)
      const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
      return fetch(`${base}/api/v1/imports/zip?overwrite_conflicts=${overwrite}`, { method: 'POST', headers, body: form })
    }
    try {
      let response = await submit(false)
      if (response.status === 409) {
        const conflict = await response.json()
        const details = conflict.detail || {}
        const ids = [...(details.item_ids || []), ...(details.outfit_ids || []).map((id: number) => `outfit #${id}`)].join(', ')
        if (!window.confirm(`Matching IDs already exist in the database: ${ids}. Update these records from the archive? Wardrobe notes will be preserved; existing photos will not be replaced.`)) return
        response = await submit(true)
      }
      const result = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof result?.detail === 'string' ? result.detail : `Import failed (${response.status})`)
      setError('')
      window.alert(`Import complete. Items added: ${result.catalog_added}; updated: ${result.catalog_updated}; photos added: ${result.photos_imported}; existing photos preserved: ${result.photos_preserved_existing}.`)
      await loadData()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Failed to import ZIP') }
    finally { if (importInput.current) importInput.current.value = '' }
  }

  const title = page === 'overview' ? 'Overview' : page === 'items' ? 'Wardrobe' : page === 'photos' ? 'Photos' : 'Outfits'
  const outfitItems = items.filter((item) => !outfitSearch || [item.id, ...Object.values(item.catalog_fields)].join(' ').toLowerCase().includes(outfitSearch.toLowerCase()))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark"><div className="brand-icon"><Shirt size={19} /></div><div><strong>MY WARDROBE</strong><small>personal catalog</small></div></div>
        <div className="side-label">MENU</div>
        <nav className="side-nav">
          <button className={page === 'overview' ? 'active' : ''} onClick={() => setPage('overview')}><Layers3 size={18} />Overview</button>
          <button className={page === 'items' ? 'active' : ''} onClick={() => setPage('items')}><Grid2X2 size={18} />All items<span className="nav-count">{stats.total_items}</span></button>
          <button className={page === 'photos' ? 'active' : ''} onClick={() => setPage('photos')}><ImageIcon size={18} />Photos</button>
          <button className={page === 'outfits' ? 'active' : ''} onClick={() => setPage('outfits')}><Sparkles size={18} />Outfits<span className="nav-count">{outfits.length}</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card"><LockKeyhole size={16} /><span>Personal data<br /><b>stored separately</b></span></div>
          <button className="settings-button" onClick={() => { setTokenDraft(token); setShowSettings(true) }}><SlidersHorizontal size={17} />Access settings</button>
          <div className="connection"><span className={`connection-dot ${error ? 'offline' : ''}`} />{error ? 'API connection unavailable' : 'Local connection'}</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div><div className="breadcrumbs">MY WARDROBE <span>/</span> {title.toLocaleUpperCase()}</div><h1>{title}</h1></div>
          <div className="top-actions"><div className="top-status"><span className={`connection-dot ${error ? 'offline' : ''}`} />{error ? 'API unavailable' : 'Synced locally'}</div><div className="export-actions"><details className="export-dropdown"><summary className="subtle-button"><Download size={15} />Export<ChevronDown size={14} /></summary><div className="export-options"><button onClick={() => void exportData('zip')}>Full ZIP archive</button><button onClick={() => void exportData('catalog.csv')}>Catalog CSV</button><button onClick={() => void exportData('catalog.json')}>Catalog JSON</button></div></details><button className="subtle-button import-button" onClick={() => importInput.current?.click()}><Upload size={15} />Import ZIP</button><input ref={importInput} type="file" accept=".zip,application/zip" hidden onChange={(event) => void importArchive(event.target.files?.[0])} /></div><button className="icon-button" title="Configure connection" onClick={() => { setTokenDraft(token); setShowSettings(true) }}><LockKeyhole size={18} /></button></div>
        </header>

        {error && <div className="alert"><CircleHelp size={17} /><span>{error}. Check that the backend is running and verify the access token in settings.</span><button onClick={() => void loadData()}>Retry</button></div>}
        {busy && !items.length && <div className="loading-line"><LoaderCircle size={17} className="spin" />Loading wardrobe…</div>}

        {page === 'overview' && <Overview stats={stats} outfits={outfits.length} openItems={() => setPage('items')} openPhotos={() => setPage('photos')} />}

        {page === 'items' && <section className="page-content">
          <div className="catalog-toolbar"><label className="search-box"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by ID, description, or brand…" /></label><span className="result-count">{filteredItems.length} items</span><label className="sort-control"><ArrowDownUp size={15} /><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="id">By ID</option><option value="category">By category</option><option value="color">By color</option><option value="brand">By brand</option></select></label></div>
          <FilterBar items={items} filters={filters} setFilters={setFilters} />
          {filteredItems.length ? <div className="item-grid">{filteredItems.map((item) => <ItemCard key={`${item.id}-${tokenVersion}`} item={item} onClick={() => setSelected(item)} />)}</div> : <Empty title="No items found" text="Adjust your search or clear the filters." />}
        </section>}

        {page === 'photos' && <section className="page-content">
          <div className="section-intro"><div><p>Review original photos and add missing ones manually.</p><span>{stats.with_photos} photos · {stats.without_photos} without photos</span></div><button className="subtle-button" onClick={() => void loadData()}><ArrowDownUp size={15} />Refresh statuses</button></div>
          <div className="photo-management-grid">{items.map((item) => <article className="photo-manage-card" key={item.id}>
            <button className="photo-manage-image" onClick={() => setSelected(item)}><ItemPhoto key={`${item.id}-${tokenVersion}`} id={item.id} /></button>
            <div className="photo-manage-meta"><b>{item.id}</b><span className={`photo-status ${item.image_status === 'missing_url' ? 'missing' : item.image_status === 'manual_upload' ? 'manual' : 'original'}`}>{item.image_status === 'manual_upload' ? 'Uploaded manually' : ['downloaded','already_exists'].includes(item.image_status) ? 'Catalog original' : 'No photo'}</span></div>
            <label className="upload-button"><Plus size={14} />{['downloaded','already_exists','manual_upload'].includes(item.image_status) ? 'Replace photo' : 'Add photo'}<input type="file" accept="image/*" onChange={(event) => { void uploadPhoto(item, event.target.files?.[0]); event.currentTarget.value = '' }} /></label>
          </article>)}</div>
        </section>}

        {page === 'outfits' && <section className="page-content">
          <div className="section-intro"><div><p>Build outfits manually from items in your catalog.</p><span>{outfits.length} saved outfits</span></div><button className="primary-button" onClick={() => openComposer()}><Plus size={17} />New outfit</button></div>
          {outfits.length ? <div className="outfit-grid">{outfits.map((outfit) => <article className="outfit-card" key={outfit.id}><div className="outfit-mosaic">{outfit.item_ids.slice(0,4).map((id) => <ItemPhoto key={`${outfit.id}-${id}-${tokenVersion}`} id={id} />)}{!outfit.item_ids.length && <div className="empty-mosaic"><Sparkles size={25} /></div>}</div><div className="outfit-body"><div className="outfit-tags">{outfit.season && <span>{outfit.season}</span>}{outfit.occasion && <span>{outfit.occasion}</span>}</div><h3>{outfit.name}</h3><p>{outfit.description || 'No description'}</p><div className="outfit-foot"><span>{outfit.item_ids.length} items · {outfit.item_ids.join(', ') || 'empty outfit'}</span><div><button className="text-button" onClick={() => openComposer(outfit)}>Edit</button><button className="text-button danger-text" onClick={() => void deleteOutfit(outfit.id)}>Delete</button></div></div></div></article>)}</div> : <Empty title="No saved outfits yet" text="Create your first outfit from your wardrobe." action={<button className="primary-button" onClick={() => openComposer()}><Plus size={17} />Create outfit</button>} />}
        </section>}
      </main>

      {selected && <ItemDetail item={items.find((item) => item.id === selected.id) || selected} close={() => setSelected(null)} tokenVersion={tokenVersion} onSave={saveItem} />}
      {composer && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setComposer(false) }}><section className="composer-modal"><header><div><div className="eyebrow">OUTFIT BUILDER</div><h2>{editingOutfit ? 'Edit outfit' : 'New outfit'}</h2></div><button className="icon-button" onClick={() => setComposer(false)}><X size={19} /></button></header><div className="composer-form"><label>Name<input autoFocus value={outfitDraft.name} onChange={(event) => setOutfitDraft({ ...outfitDraft, name: event.target.value })} placeholder="For example, a cool-weather walk" /></label><div className="form-row"><label>Season<input value={outfitDraft.season} onChange={(event) => setOutfitDraft({ ...outfitDraft, season: event.target.value })} placeholder="Spring" /></label><label>Occasion<input value={outfitDraft.occasion} onChange={(event) => setOutfitDraft({ ...outfitDraft, occasion: event.target.value })} placeholder="Casual" /></label></div><label>Description<textarea rows={2} value={outfitDraft.description} onChange={(event) => setOutfitDraft({ ...outfitDraft, description: event.target.value })} placeholder="Notes about this outfit" /></label><div className="item-pick-header"><b>Select items <small>{outfitDraft.item_ids.length} selected</small></b><label className="mini-search"><Search size={14} /><input value={outfitSearch} onChange={(event) => setOutfitSearch(event.target.value)} placeholder="Find an item" /></label></div><div className="item-picker">{outfitItems.map((item) => { const checked = outfitDraft.item_ids.includes(item.id); return <button className={`pick-item ${checked ? 'chosen' : ''}`} key={item.id} onClick={() => setOutfitDraft({ ...outfitDraft, item_ids: checked ? outfitDraft.item_ids.filter((id) => id !== item.id) : [...outfitDraft.item_ids, item.id] })}><span className="pick-check">{checked && <Check size={13} />}</span><b>{item.id}</b><span>{display(item.catalog_fields.subcategory)}</span></button> })}</div></div><footer><button className="subtle-button" onClick={() => setComposer(false)}>Cancel</button><button className="primary-button" disabled={busy} onClick={() => void saveOutfit()}>{busy ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}{editingOutfit ? 'Save changes' : 'Save outfit'}</button></footer></section></div>}

      {showSettings && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowSettings(false) }}><section className="settings-modal"><header><div><div className="eyebrow">API CONNECTION</div><h2>Access settings</h2></div><button className="icon-button" onClick={() => setShowSettings(false)}><X size={19} /></button></header><p>Leave this field empty for a local backend. For a hosted API, enter an access token. It is stored only in this browser and is never included in the source code.</p><label>Bearer token<input type="password" autoComplete="off" value={tokenDraft} onChange={(event) => setTokenDraft(event.target.value)} placeholder="Leave empty for local mode" /></label><footer><button className="subtle-button" onClick={() => setShowSettings(false)}>Cancel</button><button className="primary-button" onClick={pickToken}><Check size={16} />Save</button></footer></section></div>}
    </div>
  )
}

function Overview({ stats, outfits, openItems, openPhotos }: { stats: Stats; outfits: number; openItems: () => void; openPhotos: () => void }) {
  const categories = Object.entries(stats.by_category).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...categories.map(([, count]) => count))
  const seasons = Object.entries(stats.by_season).sort((a, b) => b[1] - a[1]).slice(0, 5)
  return <section className="page-content overview-content">
    <div className="welcome-row"><div><div className="eyebrow">YOUR WARDROBE</div><h2>What you already own</h2><p>A personal catalog with photos and details for every item.</p></div><button className="primary-button" onClick={openItems}><Grid2X2 size={16} />Open catalog</button></div>
    <div className="stats-row"><StatCard label="Total items" value={stats.total_items} note="permanent IDs W001–W139" icon={<Shirt size={19} />} /><StatCard label="With photos" value={stats.with_photos} note={stats.total_items ? `${Math.round(stats.with_photos / stats.total_items * 100)}% of catalog` : 'Local originals'} icon={<ImageIcon size={19} />} /><StatCard label="Without photos" value={stats.without_photos} note="photos can be added manually" icon={<ImageIcon size={19} />} action={openPhotos} /><StatCard label="Saved outfits" value={outfits} note="manually created looks" icon={<Heart size={19} />} /></div>
    <div className="overview-panels"><section className="panel category-panel"><div className="panel-heading"><div><span className="eyebrow">WARDROBE</span><h3>By category</h3></div><button className="text-button" onClick={openItems}>All items <ChevronDown size={14} className="rotate-left" /></button></div>{categories.map(([name, count]) => <div className="bar-row" key={name}><div className="bar-label"><span>{categoryLabels[name] || titleCase(name)}</span><b>{count}</b></div><div className="bar-track"><div style={{ width: `${count / max * 100}%` }} /></div></div>)}</section><section className="panel season-panel"><div className="panel-heading"><div><span className="eyebrow">SEASONS</span><h3>In catalog descriptions</h3></div><Sparkles size={18} className="muted-icon" /></div>{seasons.map(([name, count]) => <div className="season-row" key={name}><span>{name === 'Unspecified' ? 'Not specified' : name}</span><b>{count}</b></div>)}<div className="data-note"><CircleHelp size={15} />Blank attributes are left unspecified.</div></section></div>
    <div className="notice-strip"><div className="notice-icon"><Cloud size={18} /></div><div><b>Private by default</b><span>Photos and tables stay separate from the public source code.</span></div><button onClick={openPhotos}>Manage photos <ChevronDown size={14} className="rotate-left" /></button></div>
  </section>
}

function StatCard({ label, value, note, icon, action }: { label: string; value: number; note: string; icon: React.ReactNode; action?: () => void }) {
  return <button className={`stat-card ${action ? 'stat-clickable' : ''}`} onClick={action}><div className="stat-card-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong><small>{note}</small></button>
}

function FilterBar({ items, filters, setFilters }: { items: WardrobeItem[]; filters: Filters; setFilters: React.Dispatch<React.SetStateAction<Filters>> }) {
  const set = (key: string, value: string) => setFilters({ ...filters, [key]: value })
  const categories = [...new Set(items.map((item) => item.catalog_fields.category).filter(Boolean))].sort()
  const statuses = [...new Set(items.map((item) => item.catalog_fields.status).filter(Boolean))].sort()
  const select = (key: keyof Filters, label: string, choices: string[]) => <label className="filter-select" key={key}><span>{label}</span><select value={filters[key]} onChange={(event) => set(key, event.target.value)}><option value="">All</option>{choices.map((choice) => <option key={choice} value={choice}>{key === 'has_photo' ? choice === 'yes' ? 'Yes' : 'No' : choice}</option>)}</select></label>
  const active = Object.values(filters).some(Boolean)
  return <div className="filters-wrap"><div className="filters-title"><ListFilter size={16} /><span>Filters</span>{active && <button onClick={() => setFilters({ category: '', subcategory: '', color: '', season: '', formality: '', warmth: '', fit: '', brand: '', status: '', has_photo: '' })}>Clear</button>}</div><div className="filters-grid">{select('category','Category',categories)}<label className="filter-select"><span>Subcategory</span><input value={filters.subcategory} onChange={(event) => set('subcategory', event.target.value)} placeholder="Any" /></label><label className="filter-select"><span>Color</span><input value={filters.color} onChange={(event) => set('color', event.target.value)} placeholder="Any color" /></label><label className="filter-select"><span>Season</span><input value={filters.season} onChange={(event) => set('season', event.target.value)} placeholder="Any" /></label><label className="filter-select"><span>Formality</span><input value={filters.formality} onChange={(event) => set('formality', event.target.value)} placeholder="Any" /></label><label className="filter-select"><span>Warmth</span><input value={filters.warmth} onChange={(event) => set('warmth', event.target.value)} placeholder="Any" /></label><label className="filter-select"><span>Fit</span><input value={filters.fit} onChange={(event) => set('fit', event.target.value)} placeholder="Any" /></label><label className="filter-select"><span>Brand</span><input value={filters.brand} onChange={(event) => set('brand', event.target.value)} placeholder="Any" /></label>{select('status','Status',statuses)}{select('has_photo','Photo',['yes','no'])}</div></div>
}

function ItemCard({ item, onClick }: { item: WardrobeItem; onClick: () => void }) {
  const fields = item.catalog_fields
  return <button className="item-card" onClick={onClick}><div className="item-card-photo"><ItemPhoto id={item.id} alt={item.id} /><span className="item-id">{item.id}</span>{item.image_status === 'manual_upload' && <span className="manual-mark">Manual photo</span>}</div><div className="item-card-info"><div className="item-card-title"><strong>{display(fields.subcategory)}</strong><span>{display(fields.primary_color)}</span></div><div className="item-card-meta"><span>{categoryLabels[fields.category] || display(fields.category)}</span>{fields.brand && <><i /> <span>{fields.brand}</span></>}{fields.season && <><i /> <span>{fields.season}</span></>}</div></div></button>
}

function ItemDetail({ item, close, tokenVersion, onSave }: { item: WardrobeItem; close: () => void; tokenVersion: number; onSave: (id: string, fields: Record<string, string>, notes: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState<Record<string, string>>({ ...item.catalog_fields })
  const [notes, setNotes] = useState(item.user_notes)
  useEffect(() => { setDraft({ ...item.catalog_fields }); setNotes(item.user_notes); setEditing(false) }, [item.id, item.catalog_fields, item.user_notes])
  const fields = item.catalog_fields
  const details = Object.entries(fields).filter(([key, value]) => key !== 'id' && value?.trim())
  return <div className="detail-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close() }}><aside className="detail-panel"><header><div><span className="eyebrow">ITEM DETAILS</span><h2>{item.id}</h2></div><div className="detail-header-actions"><button className="subtle-button edit-toggle" onClick={() => setEditing(!editing)}><Pencil size={14} />{editing ? 'Cancel' : 'Edit'}</button><button className="icon-button" onClick={close}><X size={19} /></button></div></header><div className="detail-photo"><ItemPhoto key={`${item.id}-${tokenVersion}`} id={item.id} alt={item.id} /></div><div className="detail-content"><div className="detail-heading"><div><span className="eyebrow">{categoryLabels[fields.category] || fields.category}</span><h3>{display(fields.subcategory)}</h3></div><span className={`photo-status ${item.image_status === 'manual_upload' ? 'manual' : 'original'}`}>{item.image_status === 'manual_upload' ? 'Manual upload' : ['downloaded','already_exists'].includes(item.image_status) ? 'Original photo' : 'No photo'}</span></div>{item.visual_description && <div className="visual-description"><span className="eyebrow">VISUAL DESCRIPTION</span><p>{item.visual_description.visual_description}</p>{item.visual_description.critical_details && <div><b>Critical details</b><p>{item.visual_description.critical_details}</p></div>}{item.visual_description.uncertainties && <div className="uncertainties"><b>Uncertainties</b><p>{item.visual_description.uncertainties}</p></div>}</div>}<div className="detail-fields"><span className="eyebrow">CATALOG ATTRIBUTES</span>{editing ? Object.entries(draft).filter(([key]) => key !== 'id').map(([key,value]) => <label className="detail-edit-field" key={key}><span>{labels[key] || titleCase(key.replaceAll('_',' '))}</span><input value={value || ''} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} /></label>) : details.map(([key,value]) => <div className="detail-field" key={key}><span>{labels[key] || titleCase(key.replaceAll('_',' '))}</span><p>{value}</p></div>)}</div>{editing ? <div className="detail-user-notes"><label><b>My notes</b><textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label><button className="primary-button save-item-button" disabled={saving} onClick={async () => { setSaving(true); try { await onSave(item.id, draft, notes); setEditing(false) } catch { /* Error is shown in the app banner */ } finally { setSaving(false) } }}>{saving ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />}Save</button></div> : item.user_notes && <div className="detail-user-notes"><b>My notes</b><p>{item.user_notes}</p></div>}<div className="detail-footer"><Download size={15} /><span>Local file: {item.local_image_path || 'missing'}</span></div></div></aside></div>
}

function Empty({ title, text, action }: { title: string; text: string; action?: React.ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Shirt size={22} /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}
