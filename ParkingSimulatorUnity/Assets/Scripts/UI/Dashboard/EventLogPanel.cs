using System;
using System.Collections.Generic;
using UnityEngine;

namespace ParkingSim.UI.Dashboard
{
    public struct EventEntry
    {
        public string Timestamp;
        public string Message;
        public EventType Type;
    }

    public enum EventType
    {
        Info, Success, Warning, Error, Connection
    }

    public class EventLogPanel
    {
        private readonly List<EventEntry> eventLog = new List<EventEntry>();
        private readonly int maxLogEntries;
        private readonly int maxVisibleEntries;
        private Vector2 logScrollPos;

        private GUIStyle eventStyle, eventGreenStyle, eventRedStyle, eventYellowStyle;
        private bool stylesCreated;

        public EventLogPanel(int maxEntries = 50, int maxVisible = 20)
        {
            maxLogEntries = maxEntries;
            maxVisibleEntries = maxVisible;
        }

        public void AddEvent(string message, EventType type = EventType.Info)
        {
            string emoji = type switch
            {
                EventType.Success => "[OK]",
                EventType.Warning => "[!]",
                EventType.Error => "[ERR]",
                EventType.Connection => "[WS]",
                _ => "[i]"
            };

            eventLog.Add(new EventEntry
            {
                Timestamp = DateTime.Now.ToString("HH:mm:ss"),
                Message = $"{emoji} {message}",
                Type = type
            });

            if (eventLog.Count > maxLogEntries)
                eventLog.RemoveAt(0);

            logScrollPos.y = float.MaxValue;
        }

        public void EnsureStyles()
        {
            if (stylesCreated) return;
            stylesCreated = true;

            eventStyle = new GUIStyle(GUI.skin.label) { fontSize = 11, richText = true };
            eventStyle.normal.textColor = new Color(0.75f, 0.75f, 0.78f);

            eventGreenStyle = new GUIStyle(eventStyle);
            eventGreenStyle.normal.textColor = new Color(0.4f, 0.9f, 0.4f);

            eventRedStyle = new GUIStyle(eventStyle);
            eventRedStyle.normal.textColor = new Color(0.95f, 0.4f, 0.4f);

            eventYellowStyle = new GUIStyle(eventStyle);
            eventYellowStyle.normal.textColor = new Color(0.95f, 0.85f, 0.3f);
        }

        public void Draw(GUIStyle sectionStyle)
        {
            GUILayout.Label("── Events ──", sectionStyle);
            logScrollPos = GUILayout.BeginScrollView(logScrollPos, GUILayout.Height(80));

            int start = Mathf.Max(0, eventLog.Count - maxVisibleEntries);
            for (int i = start; i < eventLog.Count; i++)
            {
                var entry = eventLog[i];
                GUIStyle style = entry.Type switch
                {
                    EventType.Success => eventGreenStyle,
                    EventType.Error => eventRedStyle,
                    EventType.Warning => eventYellowStyle,
                    _ => eventStyle
                };
                GUILayout.Label($"[{entry.Timestamp}] {entry.Message}", style);
            }

            GUILayout.EndScrollView();
        }
    }
}
