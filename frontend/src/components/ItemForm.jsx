import React, { useState, useEffect } from 'react'

export default function ItemForm({ item, onSubmit, onCancel }) {
  const [name, setName] = useState('')

  useEffect(() => {
    if (item) {
      setName(item.name)
    }
  }, [item])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ ...item, name })
  }

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Item name" />
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>Cancel</button>
    </form>
  )
}
