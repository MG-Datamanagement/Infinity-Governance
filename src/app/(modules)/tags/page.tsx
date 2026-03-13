'use client'

import React, { useState, useEffect } from 'react'
import { Home, Tag, Trash2, Edit2, AlertTriangle } from 'lucide-react'
import { useGetTags, useCreateTag, useUpdateTag, useDeleteTag } from '@/hooks/useTagsQueries'
import { CreateTagRequest } from '@/types/tagTypes'
import { ApiOwner } from '@/services/dashboardApiServices'

export default function TagsPage() {
  const [showModal, setShowModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [tagToDelete, setTagToDelete] = useState<string | null>(null)
  const [editingTag, setEditingTag] = useState<string | null>(null)
  const [tagName, setTagName] = useState('')
  const [tagType, setTagType] = useState('general')
  const [description, setDescription] = useState('')
  const [securityPolicy, setSecurityPolicy] = useState('medium')
  const [selectedColor, setSelectedColor] = useState('#3B82F6')
  const [status, setStatus] = useState<'active' | 'inactive'>('active')
  const [ownerId, setOwnerId] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [owners, setOwners] = useState<ApiOwner[]>([])

  // React Query hooks
  const { data: tags = [], isLoading, error } = useGetTags({
    tag_type: typeFilter || undefined,
    status: statusFilter || undefined,
  })
  const createTagMutation = useCreateTag()
  const updateTagMutation = useUpdateTag()
  const deleteTagMutation = useDeleteTag()

  // Fetch owners list
  useEffect(() => {
    const fetchOwners = async () => {
      try {
        const { dashboardApiServices } = await import("@/services/dashboardApiServices")
        const list = await dashboardApiServices.fetchOwnersList()
        setOwners(list)
        if (list.length > 0 && !ownerId) {
          setOwnerId(list[0].id)
        }
      } catch (err) {
        console.error("Failed to fetch owners", err)
      }
    }
    fetchOwners()
  }, [])

  const colors = [
    { name: 'blue', hex: '#3B82F6', class: 'bg-blue-500' },
    { name: 'red', hex: '#EF4444', class: 'bg-red-500' },
    { name: 'orange', hex: '#FB923C', class: 'bg-orange-400' },
    { name: 'green', hex: '#10B981', class: 'bg-green-500' },
    { name: 'purple', hex: '#9C27B0', class: 'bg-purple-500' },
    { name: 'cyan', hex: '#06B6D4', class: 'bg-cyan-500' },
    { name: 'teal', hex: '#14B8A6', class: 'bg-teal-500' },
    { name: 'gray', hex: '#6B7280', class: 'bg-gray-500' }
  ]

  const handleOpenModal = (tagId?: string) => {
    if (tagId) {
      const tag = tags.find((t) => t.id === tagId)
      if (tag) {
        setEditingTag(tagId)
        setTagName(tag.name)
        setTagType(tag.tag_type)
        setDescription(tag.description)
        setSecurityPolicy(tag.security_policy)
        setSelectedColor(tag.color)
        setStatus(tag.status)
        setOwnerId(tag.owner_id)
      }
    } else {
      setEditingTag(null)
      setTagName('')
      setTagType('general')
      setDescription('')
      setSecurityPolicy('medium')
      setSelectedColor('#3B82F6')
      setStatus('active')
      setOwnerId(owners.length > 0 ? owners[0].id : '')
    }
    setShowModal(true)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingTag(null)
    setTagName('')
    setTagType('general')
    setDescription('')
    setSecurityPolicy('medium')
    setSelectedColor('#3B82F6')
    setStatus('active')
    setOwnerId(owners.length > 0 ? owners[0].id : '')
  }

  const handleCreateOrUpdateTag = async () => {
    if (!tagName.trim()) {
      alert('Please enter a tag name')
      return
    }

    if (!ownerId) {
      alert('Please select an owner')
      return
    }

    const tagData: CreateTagRequest = {
      name: tagName,
      tag_type: tagType,
      description: description,
      security_policy: securityPolicy,
      color: selectedColor,
      status: status,
      owner_id: ownerId,
    }

    try {
      if (editingTag) {
        await updateTagMutation.mutateAsync({ tagId: editingTag, data: tagData })
      } else {
        await createTagMutation.mutateAsync(tagData)
      }
      handleCloseModal()
    } catch (error) {
      console.error('Error saving tag:', error)
      alert('Failed to save tag. Please try again.')
    }
  }

  const handleDeleteTag = async (tagId: string) => {
    setTagToDelete(tagId)
    setShowDeleteModal(true)
  }

  const confirmDeleteTag = async () => {
    if (!tagToDelete) return

    try {
      await deleteTagMutation.mutateAsync(tagToDelete)
      setShowDeleteModal(false)
      setTagToDelete(null)
    } catch (error) {
      console.error('Error deleting tag:', error)
      alert('Failed to delete tag. Please try again.')
    }
  }

  const cancelDelete = () => {
    setShowDeleteModal(false)
    setTagToDelete(null)
  }

  const filteredTags = tags.filter((tag) => {
    const matchesSearch = tag.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tag.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-600 mb-4">
          <Home className="w-4 h-4 text-indigo-600" />
          <span className="text-indigo-600">Home</span>
          <span>&gt;</span>
          <span>Governance</span>
          <span>&gt;</span>
          <span className="text-gray-900">Tags</span>
        </nav>

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Tag className="w-6 h-6 text-gray-700" />
              <h1 className="text-3xl font-semibold text-gray-900">Tag Management</h1>
            </div>
            <p className="text-gray-600">Configure and manage global tags for data classification, privacy, and retention.</p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            <span className="text-lg">+</span>
            Create Tag
          </button>
        </div>

        {/* Search and Filters */}
        <div className="bg-white p-4 rounded-lg shadow-sm mb-6 border border-gray-200">
          <div className="flex gap-4 items-center">
            <div className="flex-1 relative">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 pl-10 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Search tags by name or description..."
              />
              <svg className="w-5 h-5 text-gray-400 absolute left-3 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Filters:</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Types</option>
                <option value="privacy">Privacy</option>
                <option value="classification">Classification</option>
                <option value="retention">Retention</option>
                <option value="general">General</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Loading and Error States */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="mt-2 text-gray-600">Loading tags...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Error loading tags. Please try again.
          </div>
        )}

        {/* Table */}
        {!isLoading && !error && (
          <div className="bg-white rounded-lg shadow-sm overflow-hidden border border-gray-200">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tag Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Security</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTags.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                      No tags found. Create your first tag to get started.
                    </td>
                  </tr>
                ) : (
                  filteredTags.map((tag) => (
                    <tr key={tag.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <span
                            className="inline-block w-3 h-3 rounded-full"
                            style={{ backgroundColor: tag.color }}
                          />
                          <span className="text-sm font-medium text-gray-900">{tag.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5 text-sm text-gray-700 bg-gray-100 rounded-full px-3 py-1">
                          <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                          </svg>
                          {tag.tag_type}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-sm text-gray-600 truncate max-w-md">{tag.description}</p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${
                          tag.status === 'active' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            tag.status === 'active' ? 'bg-green-600' : 'bg-gray-600'
                          }`} />
                          {tag.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                          tag.security_policy === 'high' ? 'bg-red-100 text-red-700' :
                          tag.security_policy === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {tag.security_policy}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleOpenModal(tag.id)}
                            className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                            title="Edit tag"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteTag(tag.id)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete tag"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Delete Tag</h2>
                  <p className="text-sm text-gray-600 mt-1">This action cannot be undone</p>
                </div>
              </div>

              <p className="text-gray-700 mb-6">
                Are you sure you want to delete this tag? This will remove the tag from all associated datasets and columns.
              </p>

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={cancelDelete}
                  disabled={deleteTagMutation.isPending}
                  className="px-6 py-2.5 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmDeleteTag}
                  disabled={deleteTagMutation.isPending}
                  className="px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50"
                >
                  {deleteTagMutation.isPending ? 'Deleting...' : 'Delete Tag'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Tag Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {editingTag ? 'Edit Tag' : 'Create New Tag'}
                </h2>
                <p className="text-sm text-gray-600 mt-1">Define the properties and policies for this tag.</p>
              </div>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="tagName" className="block text-sm font-medium text-gray-700 mb-2">
                    Tag Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="tagName"
                    type="text"
                    value={tagName}
                    onChange={(e) => setTagName(e.target.value)}
                    placeholder="e.g. PII, Confidential"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label htmlFor="tagType" className="block text-sm font-medium text-gray-700 mb-2">
                    Tag Type
                  </label>
                  <select
                    id="tagType"
                    value={tagType}
                    onChange={(e) => setTagType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="general">General</option>
                    <option value="privacy">Privacy</option>
                    <option value="classification">Classification</option>
                    <option value="retention">Retention</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe when and how this tag should be applied..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="securityPolicy" className="block text-sm font-medium text-gray-700 mb-2">
                    Security Policy
                  </label>
                  <select
                    id="securityPolicy"
                    value={securityPolicy}
                    onChange={(e) => setSecurityPolicy(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="owner" className="block text-sm font-medium text-gray-700 mb-2">
                    Owner <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="owner"
                    value={ownerId}
                    onChange={(e) => setOwnerId(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white cursor-pointer"
                  >
                    <option value="">Select an owner</option>
                    {owners.map((owner) => (
                      <option key={owner.id} value={owner.id}>
                        {owner.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="block text-sm font-medium text-gray-700 mb-3">
                    Color Indicator
                  </span>
                  <div className="flex gap-2">
                    {colors.map((color) => (
                      <button
                        key={color.name}
                        type="button"
                        onClick={() => setSelectedColor(color.hex)}
                        className={`w-8 h-8 rounded-full ${color.class} ${
                          selectedColor === color.hex 
                            ? 'ring-2 ring-offset-2 ring-gray-400' 
                            : 'hover:ring-2 hover:ring-offset-2 hover:ring-gray-300'
                        } transition-all`}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <span className="block text-sm font-medium text-gray-700 mb-3">
                    Status
                  </span>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setStatus('active')}
                      className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                        status === 'active'
                          ? 'border-green-500 bg-green-50 text-green-700 font-medium'
                          : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Active
                    </button>
                    <button
                      type="button"
                      onClick={() => setStatus('inactive')}
                      className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                        status === 'inactive'
                          ? 'border-gray-500 bg-gray-50 text-gray-700 font-medium'
                          : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Inactive
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 flex-shrink-0">
              <button
                type="button"
                onClick={handleCloseModal}
                className="px-6 py-2.5 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateOrUpdateTag}
                disabled={createTagMutation.isPending || updateTagMutation.isPending}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
              >
                {createTagMutation.isPending || updateTagMutation.isPending
                  ? 'Saving...'
                  : editingTag ? 'Update Tag' : 'Create Tag'
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
