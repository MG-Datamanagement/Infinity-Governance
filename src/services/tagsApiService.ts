import { tagsApiClient } from '@/lib/api-clients/tagsApiClient'
import { Tag, CreateTagRequest, UpdateTagRequest, GetTagsParams } from '@/types/tagTypes'

export const tagsApiService = {
  // Get all tags with optional filters
  getTags: async (params?: GetTagsParams): Promise<Tag[]> => {
    try {
      const tags = await tagsApiClient.getTags(params)
      return tags
    } catch (error) {
      console.error('Error fetching tags:', error)
      throw error
    }
  },

  // Create a new tag
  createTag: async (data: CreateTagRequest): Promise<Tag> => {
    try {
      const tag = await tagsApiClient.createTag(data)
      return tag
    } catch (error) {
      console.error('Error creating tag:', error)
      throw error
    }
  },

  // Update an existing tag
  updateTag: async (tagId: string, data: UpdateTagRequest): Promise<Tag> => {
    try {
      const tag = await tagsApiClient.updateTag(tagId, data)
      return tag
    } catch (error) {
      console.error('Error updating tag:', error)
      throw error
    }
  },

  // Delete a tag
  deleteTag: async (tagId: string): Promise<void> => {
    try {
      await tagsApiClient.deleteTag(tagId)
    } catch (error) {
      console.error('Error deleting tag:', error)
      throw error
    }
  },
}

