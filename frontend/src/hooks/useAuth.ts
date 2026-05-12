import { useMutation, useQueryClient } from '@tanstack/react-query'

import { createApiKey, login, logout } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

export function useLogin() {
  const queryClient = useQueryClient()
  const markAuthenticated = useAuthStore((state) => state.markAuthenticated)
  return useMutation({
    mutationFn: login,
    onSuccess: () => {
      markAuthenticated()
      queryClient.invalidateQueries()
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  const markAnonymous = useAuthStore((state) => state.markAnonymous)
  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      markAnonymous()
      queryClient.clear()
    },
  })
}

export function useCreateApiKey() {
  return useMutation({ mutationFn: createApiKey })
}
