import { useState, useEffect, useCallback, useRef } from 'react'
import { validate } from '../api/auth'

export interface SessionState {
  vendorId: number | null
  role: string | null
  expiresAt: Date | null
  loading: boolean
  authenticated: boolean
}

const RENEWAL_WARNING_SECONDS = 5 * 60   // show banner at 5 min remaining
const TICK_MS = 1000

export function useSession() {
  const [session, setSession] = useState<SessionState>({
    vendorId: null,
    role: null,
    expiresAt: null,
    loading: true,
    authenticated: false,
  })
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null)
  const [showRenewalBanner, setShowRenewalBanner] = useState(false)
  const [renewalDismissed, setRenewalDismissed] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const startTimer = useCallback(
    (expiresAt: Date) => {
      stopTimer()
      timerRef.current = setInterval(() => {
        const secs = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000))
        setSecondsLeft(secs)
        if (secs <= RENEWAL_WARNING_SECONDS && !renewalDismissed) {
          setShowRenewalBanner(true)
        }
        if (secs === 0) stopTimer()
      }, TICK_MS)
    },
    [stopTimer, renewalDismissed]
  )

  const refresh = useCallback(async () => {
    try {
      const data = await validate()
      const exp = new Date(data.expires_at)
      setSession({
        vendorId: data.vendor_id,
        role: data.role,
        expiresAt: exp,
        loading: false,
        authenticated: true,
      })
      setSecondsLeft(Math.max(0, Math.floor((exp.getTime() - Date.now()) / 1000)))
      startTimer(exp)
    } catch {
      setSession({ vendorId: null, role: null, expiresAt: null, loading: false, authenticated: false })
      stopTimer()
    }
  }, [startTimer, stopTimer])

  const updateExpiry = useCallback(
    (newExpiresAt: string) => {
      const exp = new Date(newExpiresAt)
      setSession((s) => ({ ...s, expiresAt: exp }))
      setRenewalDismissed(false)
      setShowRenewalBanner(false)
      startTimer(exp)
    },
    [startTimer]
  )

  const dismissRenewalBanner = useCallback(() => {
    setRenewalDismissed(true)
    setShowRenewalBanner(false)
  }, [])

  useEffect(() => {
    refresh()
    return stopTimer
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    session,
    secondsLeft,
    showRenewalBanner,
    dismissRenewalBanner,
    refresh,
    updateExpiry,
  }
}
