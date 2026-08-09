import { useEffect, useState } from 'react'

/** Re-renders on an interval; used to drive the countdown display. */
export default function useTick(intervalMs = 500): number {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return tick
}
