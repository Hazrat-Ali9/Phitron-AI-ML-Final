import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

/**
 * Wraps useMutation with the two things every write in this app needs:
 * refresh the related lists and show a toast.
 */
export function useApiMutation<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  { invalidate, success, onSuccess }: { invalidate: string[]; success?: string; onSuccess?: (data: TResult) => void },
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (data) => {
      for (const key of invalidate) qc.invalidateQueries({ queryKey: [key] })
      if (success) toast.success(success)
      onSuccess?.(data)
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
