import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tagsApiService } from '@/services/tagsApiService'
import { CreateTagRequest, UpdateTagRequest, GetTagsParams } from '@/types/tagTypes'

// Query keys
export const tagKeys = {
  all: ['tags'] as const,
  lists: () => [...tagKeys.all, 'list'] as const,
  list: (filters?: GetTagsParams) => [...tagKeys.lists(), filters] as const,
  details: () => [...tagKeys.all, 'detail'] as const,
  detail: (id: string) => [...tagKeys.details(), id] as const,
}

// Get tags query
export const useGetTags = (params?: GetTagsParams) => {
  return useQuery({
    queryKey: tagKeys.list(params),
    queryFn: () => tagsApiService.getTags(params),
  })
}

// Create tag mutation
export const useCreateTag = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTagRequest) => tagsApiService.createTag(data),
    onSuccess: () => {
      // Invalidate all tag queries to refetch data
      queryClient.invalidateQueries({ queryKey: tagKeys.lists() })
    },
  })
}

// Update tag mutation
export const useUpdateTag = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ tagId, data }: { tagId: string; data: UpdateTagRequest }) =>
      tagsApiService.updateTag(tagId, data),
    onSuccess: () => {
      // Invalidate all tag queries to refetch data
      queryClient.invalidateQueries({ queryKey: tagKeys.lists() })
    },
  })
}

// Delete tag mutation
export const useDeleteTag = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (tagId: string) => tagsApiService.deleteTag(tagId),
    onSuccess: () => {
      // Invalidate all tag queries to refetch data
      queryClient.invalidateQueries({ queryKey: tagKeys.lists() })
    },
  })
}
