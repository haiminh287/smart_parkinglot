using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using ParkingSim.Navigation;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class WaypointGraphTests
    {
        private GameObject graphGo;
        private WaypointGraph graph;
        private List<GameObject> createdObjects;

        [SetUp]
        public void SetUp()
        {
            graphGo = new GameObject("WaypointGraph");
            graph = graphGo.AddComponent<WaypointGraph>();
            createdObjects = new List<GameObject> { graphGo };
        }

        [TearDown]
        public void TearDown()
        {
            foreach (var go in createdObjects)
            {
                if (go != null)
                    Object.DestroyImmediate(go);
            }
            createdObjects.Clear();
        }

        [Test]
        public void should_register_node_and_assign_id()
        {
            // Arrange
            var node = CreateNode("Node_0", Vector3.zero, WaypointNode.NodeType.Lane);

            // Act
            int id = graph.RegisterNode(node);

            // Assert
            Assert.AreEqual(0, id, "First registered node should get id=0");
            Assert.AreEqual(0, node.nodeId);
            Assert.AreEqual(1, graph.NodeCount);
        }

        [Test]
        public void should_assign_incremental_ids()
        {
            // Arrange
            var nodeA = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            var nodeB = CreateNode("B", Vector3.right, WaypointNode.NodeType.Lane);
            var nodeC = CreateNode("C", Vector3.forward, WaypointNode.NodeType.Lane);

            // Act
            int idA = graph.RegisterNode(nodeA);
            int idB = graph.RegisterNode(nodeB);
            int idC = graph.RegisterNode(nodeC);

            // Assert
            Assert.AreEqual(0, idA);
            Assert.AreEqual(1, idB);
            Assert.AreEqual(2, idC);
            Assert.AreEqual(3, graph.NodeCount);
        }

        [Test]
        public void should_connect_nodes_bidirectionally()
        {
            // Arrange
            var nodeA = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            var nodeB = CreateNode("B", Vector3.right * 5, WaypointNode.NodeType.Lane);
            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);

            // Act
            graph.Connect(nodeA, nodeB);

            // Assert — bidirectional connection
            Assert.IsTrue(nodeA.connections.Contains(nodeB),
                "A should have B in its connections");
            Assert.IsTrue(nodeB.connections.Contains(nodeA),
                "B should have A in its connections");
        }

        [Test]
        public void should_not_connect_node_to_itself()
        {
            // Arrange
            var node = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            graph.RegisterNode(node);

            // Act
            graph.Connect(node, node);

            // Assert
            Assert.AreEqual(0, node.connections.Count, "Node should not connect to itself");
        }

        [Test]
        public void should_find_path_with_BFS()
        {
            // Arrange — linear graph: A → B → C → D
            var nodeA = CreateNode("A", new Vector3(0, 0, 0), WaypointNode.NodeType.Gate);
            var nodeB = CreateNode("B", new Vector3(5, 0, 0), WaypointNode.NodeType.Lane);
            var nodeC = CreateNode("C", new Vector3(10, 0, 0), WaypointNode.NodeType.Lane);
            var nodeD = CreateNode("D", new Vector3(15, 0, 0), WaypointNode.NodeType.SlotEntrance, "A-01");

            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);
            graph.RegisterNode(nodeC);
            graph.RegisterNode(nodeD);

            graph.Connect(nodeA, nodeB);
            graph.Connect(nodeB, nodeC);
            graph.Connect(nodeC, nodeD);

            // Act
            List<WaypointNode> path = graph.FindPath(nodeA, nodeD);

            // Assert
            Assert.IsNotNull(path);
            Assert.AreEqual(4, path.Count, "Path should be A → B → C → D");
            Assert.AreEqual(nodeA, path[0]);
            Assert.AreEqual(nodeB, path[1]);
            Assert.AreEqual(nodeC, path[2]);
            Assert.AreEqual(nodeD, path[3]);
        }

        [Test]
        public void should_find_shortest_path_in_branching_graph()
        {
            // Arrange — graph with shortcut:
            //   A → B → C → D
            //   A → D (direct)
            var nodeA = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Gate);
            var nodeB = CreateNode("B", Vector3.right * 5, WaypointNode.NodeType.Lane);
            var nodeC = CreateNode("C", Vector3.right * 10, WaypointNode.NodeType.Lane);
            var nodeD = CreateNode("D", Vector3.right * 15, WaypointNode.NodeType.SlotEntrance, "A-01");

            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);
            graph.RegisterNode(nodeC);
            graph.RegisterNode(nodeD);

            graph.Connect(nodeA, nodeB);
            graph.Connect(nodeB, nodeC);
            graph.Connect(nodeC, nodeD);
            graph.Connect(nodeA, nodeD); // shortcut

            // Act
            List<WaypointNode> path = graph.FindPath(nodeA, nodeD);

            // Assert — BFS finds shortest path: A → D
            Assert.AreEqual(2, path.Count, "BFS should find direct path A → D");
            Assert.AreEqual(nodeA, path[0]);
            Assert.AreEqual(nodeD, path[1]);
        }

        [Test]
        public void should_return_empty_path_when_no_route()
        {
            // Arrange — two disconnected nodes
            var nodeA = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            var nodeB = CreateNode("B", Vector3.right * 100, WaypointNode.NodeType.Lane);
            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);
            // No connection!

            // Act
            List<WaypointNode> path = graph.FindPath(nodeA, nodeB);

            // Assert
            Assert.IsNotNull(path);
            Assert.AreEqual(0, path.Count, "Should return empty path for disconnected nodes");
        }

        [Test]
        public void should_return_single_node_path_when_from_equals_to()
        {
            // Arrange
            var node = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            graph.RegisterNode(node);

            // Act
            List<WaypointNode> path = graph.FindPath(node, node);

            // Assert
            Assert.AreEqual(1, path.Count);
            Assert.AreEqual(node, path[0]);
        }

        [Test]
        public void should_find_nearest_node()
        {
            // Arrange
            var nodeA = CreateNode("A", new Vector3(0, 0, 0), WaypointNode.NodeType.Lane);
            var nodeB = CreateNode("B", new Vector3(10, 0, 0), WaypointNode.NodeType.Lane);
            var nodeC = CreateNode("C", new Vector3(50, 0, 0), WaypointNode.NodeType.Lane);
            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);
            graph.RegisterNode(nodeC);

            // Act — query point closest to B
            WaypointNode nearest = graph.GetNearestNode(new Vector3(8, 0, 0));

            // Assert
            Assert.AreEqual(nodeB, nearest, "Node B at (10,0,0) is nearest to query (8,0,0)");
        }

        [Test]
        public void should_find_slot_entrance_by_code()
        {
            // Arrange
            var slotNode = CreateNode("SlotA01", new Vector3(5, 0, 5),
                WaypointNode.NodeType.SlotEntrance, "A-01");
            graph.RegisterNode(slotNode);

            // Act
            WaypointNode found = graph.GetSlotEntrance("A-01");

            // Assert
            Assert.IsNotNull(found);
            Assert.AreEqual(slotNode, found);
            Assert.AreEqual("A-01", found.associatedSlotCode);
        }

        [Test]
        public void should_return_null_for_unknown_slot_code()
        {
            // Act
            WaypointNode found = graph.GetSlotEntrance("Z-99");

            // Assert
            Assert.IsNull(found);
        }

        [Test]
        public void should_return_null_for_null_slot_code()
        {
            // Act
            WaypointNode found = graph.GetSlotEntrance(null);

            // Assert
            Assert.IsNull(found);
        }

        [Test]
        public void should_find_gate_node()
        {
            // Arrange
            var gateIn = CreateNode("GateIn", new Vector3(0, 0, -10),
                WaypointNode.NodeType.Gate, "GATE-IN-01");
            var gateOut = CreateNode("GateOut", new Vector3(0, 0, 10),
                WaypointNode.NodeType.Gate, "GATE-OUT-01");
            graph.RegisterNode(gateIn);
            graph.RegisterNode(gateOut);

            // Act
            WaypointNode foundIn = graph.GetGateNode("GATE-IN-01");
            WaypointNode foundOut = graph.GetGateNode("GATE-OUT-01");

            // Assert
            Assert.AreEqual(gateIn, foundIn);
            Assert.AreEqual(gateOut, foundOut);
        }

        [Test]
        public void should_return_null_for_unknown_gate()
        {
            // Act
            WaypointNode found = graph.GetGateNode("GATE-NONEXISTENT");

            // Assert
            Assert.IsNull(found);
        }

        [Test]
        public void should_clear_all_nodes()
        {
            // Arrange
            var nodeA = CreateNode("A", Vector3.zero, WaypointNode.NodeType.Lane);
            var nodeB = CreateNode("B", Vector3.right, WaypointNode.NodeType.Lane);
            graph.RegisterNode(nodeA);
            graph.RegisterNode(nodeB);
            graph.Connect(nodeA, nodeB);

            Assert.AreEqual(2, graph.NodeCount, "Precondition: 2 nodes registered");

            // Act
            graph.Clear();

            // Assert
            Assert.AreEqual(0, graph.NodeCount, "NodeCount should be 0 after clear");
            Assert.IsNull(graph.GetSlotEntrance("A-01"), "Slot map should be cleared");
            Assert.IsNull(graph.GetGateNode("GATE-IN-01"), "Gate lookup should find nothing");
        }

        // ─── Helper ──────────────────────────────────────────

        private WaypointNode CreateNode(string name, Vector3 position,
            WaypointNode.NodeType type, string slotCode = null)
        {
            var go = new GameObject($"WP_{name}");
            go.transform.position = position;
            var node = go.AddComponent<WaypointNode>();
            node.nodeType = type;
            node.associatedSlotCode = slotCode;
            createdObjects.Add(go);
            return node;
        }
    }
}
