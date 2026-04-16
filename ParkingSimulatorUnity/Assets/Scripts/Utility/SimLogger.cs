using UnityEngine;

namespace ParkingSim.Utility
{
    public enum LogLevel { None, Error, Warning, Info, Verbose }

    public static class SimLogger
    {
        public static LogLevel Level = LogLevel.Info;

        public static void Verbose(string tag, string msg)
        {
            if (Level >= LogLevel.Verbose) Debug.Log($"[{tag}] {msg}");
        }

        public static void Info(string tag, string msg)
        {
            if (Level >= LogLevel.Info) Debug.Log($"[{tag}] {msg}");
        }

        public static void Warn(string tag, string msg)
        {
            if (Level >= LogLevel.Warning) Debug.LogWarning($"[{tag}] {msg}");
        }

        public static void Error(string tag, string msg)
        {
            if (Level >= LogLevel.Error) Debug.LogError($"[{tag}] {msg}");
        }
    }
}
