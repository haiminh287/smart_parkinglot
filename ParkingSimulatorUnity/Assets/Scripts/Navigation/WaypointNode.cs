using System.Collections.Generic;
using UnityEngine;

namespace ParkingSim.Navigation
{
    public class WaypointNode : MonoBehaviour
    {
        public enum NodeType { Gate, Lane, SlotEntrance, Ramp, Intersection }

        public int nodeId = -1;
        public List<WaypointNode> connections = new List<WaypointNode>();
        public NodeType nodeType = NodeType.Lane;
        public string associatedSlotCode;

        public void AddConnection(WaypointNode other)
        {
            if (other == null || other == this) return;
            if (!connections.Contains(other))
                connections.Add(other);
            if (!other.connections.Contains(this))
                other.connections.Add(this);
        }

        public void RemoveConnection(WaypointNode other)
        {
            if (other == null) return;
            connections.Remove(other);
            other.connections.Remove(this);
        }

#if UNITY_EDITOR
        private void OnDrawGizmos()
        {
            Gizmos.color = GetGizmoColor();
            Gizmos.DrawSphere(transform.position, 0.3f);

            Gizmos.color = Color.cyan;
            foreach (var conn in connections)
            {
                if (conn != null)
                    Gizmos.DrawLine(transform.position, conn.transform.position);
            }
        }

        private Color GetGizmoColor()
        {
            switch (nodeType)
            {
                case NodeType.Gate:         return Color.red;
                case NodeType.Lane:         return Color.blue;
                case NodeType.SlotEntrance: return Color.green;
                case NodeType.Ramp:         return Color.yellow;
                case NodeType.Intersection: return Color.white;
                default:                    return Color.blue;
            }
        }
#endif
    }
}
