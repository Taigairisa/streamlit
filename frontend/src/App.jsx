import React, { useState, useEffect } from 'react'
import { listItems, createItem, updateItem, deleteItem } from './api'
import ItemList from './components/ItemList'
import ItemForm from './components/ItemForm'

export default function App() {
  const [items, setItems] = useState([])
  const [view, setView] = useState('list')
  const [editingItem, setEditingItem] = useState(null)

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    const data = await listItems()
    setItems(data)
  }

  const handleCreate = async (item) => {
    await createItem(item)
    await fetchItems()
    setView('list')
  }

  const handleUpdate = async (item) => {
    await updateItem(item)
    await fetchItems()
    setView('list')
  }

  const handleDelete = async (id) => {
    await deleteItem(id)
    await fetchItems()
  }

  const startEdit = (item) => {
    setEditingItem(item)
    setView('edit')
  }

  return (
    <div>
      <h1>Items</h1>
      {view === 'list' && (
        <>
          <button onClick={() => setView('create')}>Create Item</button>
          <ItemList items={items} onEdit={startEdit} onDelete={handleDelete} />
        </>
      )}
      {view === "create" && (
        <ItemForm onSubmit={handleCreate} onCancel={() => setView("list")} />
      )}
      {view === "edit" && (
        <ItemForm item={editingItem} onSubmit={handleUpdate} onCancel={() => setView("list")} />
      )}
    </div>
  )
}
