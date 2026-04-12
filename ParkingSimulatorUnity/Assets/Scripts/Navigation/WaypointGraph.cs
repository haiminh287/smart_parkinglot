using System.Collections.Generic;
using UnityEngine;

namespace ParkingSim.Navigation
{
    public class WaypointGraph : MonoBehaviour
    {
        private Dictionary<int, WaypointNode> nodes = new Dictionary<int, WaypointNode>();
        private Dictionary<int, List<int>> adjacency = new Dictionary<int, List<int>>();
        private Dictionary<string, WaypointNode> slotEntranceMap = new Dictionary<string, WaypointNode>();
        private int nextNodeId;

        public int NodeCount => nodes.Count;

        public int RegisterNode(WaypointNode node)
        {
            int id = nextNodeId++;
            node.nodeId = id;
            nodes[id] = node;
            adjacency[id] = new List<int>();

            if (node.nodeType == WaypointNode.NodeType.SlotEntrance
                && !string.IsNullOrEmpty(node.associatedSlotCode))
            {
                slotEntranceMap[node.associatedSlotCode] = node;
            }

            return id;
        }

        public void Connect(WaypointNode a, WaypointNode b)
        {
            if (a == null || b == null || a == b) return;

            a.AddConnection(b);

            if (adjacency.ContainsKey(a.nodeId) && !adjacency[a.nodeId].Contains(b.nodeId))
                adjacency[a.nodeId].Add(b.nodeId);

            if (adjacency.ContainsKey(b.nodeId) && !adjacency[b.nodeId].Contains(a.nodeId))
                adjacency[b.nodeId].Add(a.nodeId);
        }

        public List<WaypointNode> FindPath(WaypointNode from, WaypointNode to)
        {
            if (from == null || to == null) return new List<WaypointNode>();
            if (from == to) return new List<WaypointNode> { from };

            var visited = new HashSet<int>();
            var queue = new Queue<int>();
            var parent = new Dictionary<int, int>();

            visited.Add(from.nodeId);
            queue.Enqueue(from.nodeId);
            parent[from.nodeId] = -1;

            while (queue.Count > 0)
            {
                int current = queue.Dequeue();
                if (current == to.nodeId)
                    return ReconstructPath(parent, from.nodeId, to.nodeId);

                if (!adjacency.ContainsKey(current)) continue;

                foreach (int neighbor in adjacency[current])
                {
                    if (!visited.Contains(neighbor))
                    {
                        visited.Add(neighbor);
                        parent[neighbor] = current;
                        queue.Enqueue(neighbor);
                    }
                }
            }

            Debug.LogWarning($"[WaypointGraph] No path found from node {from.nodeId} to {to.nodeId}");
            return new List<WaypointNode>();
        }

        private List<WaypointNode> ReconstructPath(Dictionary<int, int> parent, int startId, int endId)
        {
            var path = new List<WaypointNode>();
            int current = endId;

            while (current != -1)
            {
                if (nodes.ContainsKey(current))
                    path.Add(nodes[current]);
                current = parent.ContainsKey(current) ? parent[current] : -1;
            }

            path.Reverse();
            return path;
        }

        public WaypointNode GetNearestNode(Vector3 position)
        {
            WaypointNode nearest = null;
            float minDist = float.MaxValue;

            foreach (var kvp in nodes)
            {
                if (kvp.Value == null) continue;
                float dist = Vector3.SqrMagnitude(kvp.Value.transform.position - position);
                if (dist < minDist)
                {
                    minDist = dist;
                    nearest = kvp.Value;
                }
            }

            return nearest;
        }

        public WaypointNode GetNearestLaneNode(Vector3 position)
        {
            WaypointNode nearest = null;
            float minDist = float.MaxValue;
            foreach (var kvp in nodes)
            {
                if (kvp.Value == null) continue;
                if (kvp.Value.nodeType == WaypointNode.NodeType.SlotEntrance) continue;
                float dist = Vector3.SqrMagnitude(kvp.Value.transform.position - position);
                if (dist < minDist)
                {
                    minDist = dist;
                    nearest = kvp.Value;
                }
            }
            return nearest;
        }

        public WaypointNode GetSlotEntrance(string slotCode)
        {
            if (string.IsNullOrEmpty(slotCode)) return null;
            slotEntranceMap.TryGetValue(slotCode, out var node);
            return node;
        }

        public WaypointNode GetGateNode(string gateId)
        {
            foreach (var kvp in nodes)
            {
                if (kvp.Value != null
                    && kvp.Value.nodeType == WaypointNode.NodeType.Gate
                    && kvp.Value.associatedSlotCode == gateId)
                {
                    return kvp.Value;
                }
            }

            return null;
        }

        public void Clear()
        {
            foreach (var kvp in nodes)
            {
                if (kvp.Value != null)
                    Destroy(kvp.Value.gameObject);
            }

            nodes.Clear();
            adjacency.Clear();
            slotEntranceMap.Clear();
            nextNodeId = 0;
        }

#if UNITY_EDITOR
        private void OnDrawGizmos()
        {
            // Nodes draw themselves via WaypointNode.OnDrawGizmos
        }
#endif
    }
}
