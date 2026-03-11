import axios, { AxiosInstance } from 'axios'
import { Tag, CreateTagRequest, UpdateTagRequest, GetTagsParams } from '@/types/tagTypes'

class TagsApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_DEV_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // GET /api/v1/tags-list
  async getTags(params?: GetTagsParams): Promise<Tag[]> {
    const response = await this.client.get<Tag[]>('/api/v1/tags-list', { params })
    return response.data
  }

  // POST /api/v1/tags-create
  async createTag(data: CreateTagRequest): Promise<Tag> {
    const response = await this.client.post<Tag>('/api/v1/tags-create', data)
    return response.data
  }

  // PUT /api/v1/tags-update/{tag_id}
  async updateTag(tagId: string, data: UpdateTagRequest): Promise<Tag> {
    const response = await this.client.put<Tag>(`/api/v1/tags-update/${tagId}`, data)
    return response.data
  }

  // DELETE /api/v1/tags-delete/{tag_id}
  async deleteTag(tagId: string): Promise<void> {
    await this.client.delete(`/api/v1/tags-delete/${tagId}`)
  }
}

export const tagsApiClient = new TagsApiClient()

