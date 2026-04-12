using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace ParkingSim.IoT
{
    /// <summary>
    /// Captures ALL Unity log messages to a persistent log file and
    /// shows a compact overlay in Play Mode for real-time visibility.
    ///
    /// In Editor: ParkingSimulatorUnity/Logs/parksmart_flow.log
    /// In Build : Application.persistentDataPath/parksmart_flow.log
    ///
    /// Overlay shows last 12 lines; [FLOW]/[ApiService] lines are highlighted.
    /// </summary>
    public class FlowLogger : MonoBehaviour
    {
        private static FlowLogger _instance;
        public static FlowLogger Instance => _instance;

        private StreamWriter _writer;
        private string _logPath;

        private readonly Queue<string> _recentLines = new Queue<string>();
        private const int MAX_LINES = 12;

        private bool _showOverlay = true;
        private GUIStyle _logStyle;
        private GUIStyle _pathStyle;

        // Tags that get highlighted yellow in the overlay
        private static readonly string[] HIGHLIGHT_TAGS =
            { "[FLOW]", "[ApiService]", "[ESP32]", "[ParkingManager]", "[BarrierController]" };

        // ── Auto-bootstrap ───────────────────────────────────────────────── //

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (_instance != null) return;
            var go = new GameObject("FlowLogger");
            go.AddComponent<FlowLogger>();
        }

        // ── Lifecycle ────────────────────────────────────────────────────── //

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }
            _instance = this;
            DontDestroyOnLoad(gameObject);

            // Central logs folder: Project_Main/logs/unity/
            // Application.dataPath (Editor) = .../ParkingSimulatorUnity/Assets
            // ../../logs/unity  =>  Project_Main/logs/unity
#if UNITY_EDITOR
            string logsDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "logs", "unity"));
            Directory.CreateDirectory(logsDir);
            _logPath = Path.Combine(logsDir, "parksmart_unity.log");
#else
            _logPath = Path.Combine(Application.persistentDataPath, "parksmart_unity.log");
#endif
            try
            {
                _writer = new StreamWriter(_logPath, append: true) { AutoFlush = true };
                string sep = new string('=', 60);
                _writer.WriteLine();
                _writer.WriteLine(sep);
                _writer.WriteLine($"[SESSION START] {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                _writer.WriteLine(sep);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[FlowLogger] Cannot open log file: {e.Message}");
            }

            Application.logMessageReceived += OnLog;
            Debug.Log($"[FLOW] FlowLogger active → {_logPath}");
        }

        private void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            try
            {
                _writer?.WriteLine($"[SESSION END] {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                _writer?.Close();
            }
            catch { /* ignore */ }
            _writer = null;
            if (_instance == this) _instance = null;
        }

        // ── Log capture ──────────────────────────────────────────────────── //

        private void OnLog(string condition, string stackTrace, LogType type)
        {
            // Skip Unity's own internal noise and the logger's startup line
            if (condition.StartsWith("FlowLogger active")) return;

            string icon = type == LogType.Error   ? "[ERR]" :
                          type == LogType.Warning  ? "[WRN]" :
                          type == LogType.Assert   ? "[ASS]" : "[INF]";
            string line = $"[{DateTime.Now:HH:mm:ss}] {icon} {condition}";

            _writer?.WriteLine(line);

            // Stack trace on errors — helps pinpoint failures
            if ((type == LogType.Error || type == LogType.Exception) && !string.IsNullOrEmpty(stackTrace))
                _writer?.WriteLine($"         ↳ {stackTrace.Split('\n')[0].Trim()}");

            // Overlay: show only important/highlighted lines + errors
            bool isHighlighted = type == LogType.Error || type == LogType.Exception;
            if (!isHighlighted)
            {
                foreach (var tag in HIGHLIGHT_TAGS)
                {
                    if (condition.Contains(tag)) { isHighlighted = true; break; }
                }
            }

            if (isHighlighted)
            {
                lock (_recentLines)
                {
                    _recentLines.Enqueue(line);
                    while (_recentLines.Count > MAX_LINES)
                        _recentLines.Dequeue();
                }
            }
        }

        /// <summary>Write a raw line to the log file (e.g. image records, separators).</summary>
        public void WriteRaw(string text) => _writer?.WriteLine(text);

        /// <summary>Full path to the log file on disk.</summary>
        public string LogPath => _logPath;

        // ── GUI overlay ──────────────────────────────────────────────────── //

        private void OnGUI()
        {
            if (!_showOverlay)
            {
                if (GUI.Button(new Rect(10, Screen.height - 28, 120, 24), "Flow Logs"))
                    _showOverlay = true;
                return;
            }

            // Lazy-init styles (cannot be created in constructors or Awake)
            if (_logStyle == null)
            {
                _logStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 10,
                    wordWrap = false,
                    richText = false
                };
                _pathStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 9,
                    wordWrap = true
                };
                _pathStyle.normal.textColor = new Color(0.6f, 0.6f, 0.6f);
            }

            const float W = 450f;
            const float H = 235f;
            Rect area = new Rect(10, Screen.height - H - 5, W, H);

            GUI.Box(area, string.Empty);
            GUILayout.BeginArea(area);

            // Header row
            GUILayout.BeginHorizontal();
            GUILayout.Label(" [FLOW LOG]", GUILayout.ExpandWidth(true));
            if (GUILayout.Button("x", GUILayout.Width(20)))
                _showOverlay = false;
            GUILayout.EndHorizontal();

            // Log file path
            GUILayout.Label(_logPath, _pathStyle);

            GUILayout.Space(2);

            // Recent log lines
            lock (_recentLines)
            {
                foreach (var line in _recentLines)
                {
                    _logStyle.normal.textColor =
                        line.Contains("[ERR]") ? new Color(1f, 0.3f, 0.3f) :
                        line.Contains("[WRN]") ? new Color(1f, 0.75f, 0.3f) :
                        line.Contains("[FLOW]") || line.Contains("[ApiService]") ? new Color(0.5f, 1f, 0.7f) :
                        new Color(0.92f, 0.92f, 0.92f);
                    string display = line.Length > 68 ? line.Substring(0, 68) + "~" : line;
                    GUILayout.Label(display, _logStyle);
                }
            }

            GUILayout.EndArea();
        }
    }
}
