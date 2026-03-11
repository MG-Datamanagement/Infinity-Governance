// Tag Types
export interface Tag {
  id: string
  name: string
  tag_type: string
  description: string
  security_policy: string
  color: string
  status: 'active' | 'inactive'
  owner_id: string
  created_at: string
  updated_at: string
}

export interface CreateTagRequest {
  name: string
  tag_type: string
  description: string
  security_policy: string
  color: string
  status: 'active' | 'inactive'
  owner_id: string
}

export interface UpdateTagRequest {
  name?: string
  tag_type?: string
  description?: string
  security_policy?: string
  color?: string
  status?: 'active' | 'inactive'
  owner_id?: string
}

export interface GetTagsParams {
  tag_type?: string
  status?: string
}

export interface TagsResponse {
  data: Tag[]
  total: number
}

