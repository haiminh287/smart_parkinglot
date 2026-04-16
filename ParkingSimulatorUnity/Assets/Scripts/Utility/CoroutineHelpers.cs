using System;
using System.Collections;
using UnityEngine;

namespace ParkingSim.Utility
{
    /// <summary>
    /// Shared coroutine utilities cho timeout-safe waits.
    /// Extracted từ ESP32Simulator.cs line 580.
    /// </summary>
    public static class CoroutineHelpers
    {
        /// <summary>
        /// Waits until condition is true OR timeout expires.
        /// Calls onTimeout if condition never becomes true.
        /// </summary>
        /// <param name="condition">Predicate to check each frame</param>
        /// <param name="timeoutSeconds">Max wait time</param>
        /// <param name="onTimeout">Optional callback on timeout</param>
        /// <param name="debugLabel">Optional label for warning log</param>
        public static IEnumerator WaitUntilOrTimeout(
            Func<bool> condition,
            float timeoutSeconds,
            Action onTimeout = null,
            string debugLabel = null)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSeconds)
            {
                elapsed += Time.deltaTime;
                yield return null;
            }
            if (!condition())
            {
                onTimeout?.Invoke();
                if (!string.IsNullOrEmpty(debugLabel))
                    Debug.LogWarning($"[CoroutineHelpers] Timeout after {timeoutSeconds}s: {debugLabel}");
            }
        }

        /// <summary>
        /// Returns result via callback indicating whether condition became true before timeout.
        /// </summary>
        public static IEnumerator WaitWithResult(
            Func<bool> condition,
            float timeoutSeconds,
            Action<bool> result,
            string debugLabel = null)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSeconds)
            {
                elapsed += Time.deltaTime;
                yield return null;
            }
            bool succeeded = condition();
            result?.Invoke(succeeded);
            if (!succeeded && !string.IsNullOrEmpty(debugLabel))
                Debug.LogWarning($"[CoroutineHelpers] Timeout: {debugLabel}");
        }
    }
}
