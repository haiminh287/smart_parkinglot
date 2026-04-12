using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.Navigation;
using ParkingSim.Parking;

namespace ParkingSim.Vehicle
{
    public class VehicleController : MonoBehaviour
    {
        public enum VehicleState
        {
            Idle,
            ApproachingGate,
            WaitingAtGate,
            Entering,
            Navigating,
            Parking,
            Parked,
            Departing,
            WaitingAtExit,
            Exiting,
            Gone
        }

        public string plateNumber;
        public string vehicleType;
        public string bookingId;
        public string qrData;
        public ParkingSlot TargetSlot => targetSlot;
        public bool alreadyCheckedIn = false;
        public VehicleState state = VehicleState.Idle;

        /// <summary>True when vehicle has reached its slot entrance and is waiting for Verify Slot.</summary>
        public bool IsAtSlotEntrance => state == VehicleState.Navigating;

        /// <summary>Called by ParkingManager when the slot barrier opens — drives vehicle into slot.</summary>
        public void ProceedIntoSlot()
        {
            if (state != VehicleState.Navigating) return;
            state = VehicleState.Parking;
            Debug.Log($"[VehicleController] {plateNumber} proceeding into slot {targetSlot?.slotCode}");
            StartCoroutine(ParkCoroutine());
        }

        [SerializeField] private float moveSpeed = 5f;
        [SerializeField] private float rotationSpeed = 3f;

        private List<WaypointNode> currentPath;
        private int currentPathIndex;
        private WaypointGraph waypointGraph;
        private ParkingSlot targetSlot;
        private Transform entryGate;
        private Transform exitGate;

        public event Action<VehicleController> OnReachedGate;
        public event Action<VehicleController> OnParked;
        public event Action<VehicleController> OnReachedExit;
        public event Action<VehicleController> OnGone;

        public void Initialize(WaypointGraph graph, ParkingSlot slot, string plate, string qr, string vType)
        {
            waypointGraph = graph;
            targetSlot = slot;
            plateNumber = plate;
            qrData = qr;
            vehicleType = vType;
            Debug.Log($"[VehicleController] {plate} initialized, target: {slot.slotCode}");
        }

        public void StartEntry()
        {
            if (waypointGraph == null || targetSlot == null)
            {
                Debug.LogError("[VehicleController] Missing waypointGraph or targetSlot");
                state = VehicleState.Gone;
                return;
            }

            var gateNode = waypointGraph.GetGateNode("GATE-IN-01");

            if (gateNode == null)
            {
                Debug.LogError("[VehicleController] Cannot resolve GATE-IN-01");
                state = VehicleState.Gone;
                return;
            }

            // Phase 1: drive to gate only — stop and wait there for QR check-in
            currentPath = new System.Collections.Generic.List<WaypointNode> { gateNode };
            currentPathIndex = 0;
            state = VehicleState.ApproachingGate;
            Debug.Log($"[VehicleController] {plateNumber} heading to gate");
        }

        public void StartDeparture()
        {
            if (waypointGraph == null || targetSlot == null) return;

            var slotEntrance = waypointGraph.GetSlotEntrance(targetSlot.slotCode);
            var exitNode = waypointGraph.GetGateNode("GATE-OUT-01");

            if (slotEntrance == null || exitNode == null)
            {
                Debug.LogError("[VehicleController] Cannot resolve departure path");
                state = VehicleState.Gone;
                return;
            }

            currentPath = waypointGraph.FindPath(slotEntrance, exitNode);
            if (currentPath == null || currentPath.Count == 0)
            {
                Debug.LogError("[VehicleController] No departure path found!");
                state = VehicleState.Gone;
                return;
            }

            currentPathIndex = 0;
            state = VehicleState.Departing;
            Debug.Log($"[VehicleController] {plateNumber} departing, path: {currentPath.Count} nodes");
        }

        public void ProceedFromGate()
        {
            // Phase 2: build path from gate to slot entrance and drive in
            var gateNode = waypointGraph.GetGateNode("GATE-IN-01");
            var slotEntrance = waypointGraph.GetSlotEntrance(targetSlot.slotCode);

            if (gateNode == null || slotEntrance == null)
            {
                Debug.LogError($"[VehicleController] ProceedFromGate: cannot resolve path for {plateNumber}");
                state = VehicleState.Gone;
                return;
            }

            currentPath = waypointGraph.FindPath(gateNode, slotEntrance);
            if (currentPath == null || currentPath.Count == 0)
            {
                Debug.LogError($"[VehicleController] ProceedFromGate: no path found for {plateNumber}");
                state = VehicleState.Gone;
                return;
            }

            currentPathIndex = 0;
            state = VehicleState.Entering;
            Debug.Log($"[VehicleController] {plateNumber} proceeding from gate → slot");
        }

        public void ProceedFromExit()
        {
            // Build a 1-node path driving out along the exit road (-X direction)
            // so the car leaves the scene and OnPathComplete destroys it.
            var exitRoadGO = new GameObject("_ExitRoadTarget");
            exitRoadGO.transform.position = waypointGraph != null
                ? (waypointGraph.GetGateNode("GATE-OUT-01")?.transform.position ?? Vector3.zero)
                    + new Vector3(-18f, 0f, 0f)
                : new Vector3(-55f, 0.1f, 0f);
            var exitTargetNode = exitRoadGO.AddComponent<WaypointNode>();
            exitTargetNode.nodeType = WaypointNode.NodeType.Gate;

            currentPath = new System.Collections.Generic.List<WaypointNode> { exitTargetNode };
            currentPathIndex = 0;
            state = VehicleState.Exiting;

            // Auto-destroy the temp node after car is gone
            Destroy(exitRoadGO, 12f);
            Debug.Log($"[VehicleController] {plateNumber} driving out via exit road");
        }

        private void Update()
        {
            switch (state)
            {
                case VehicleState.ApproachingGate:
                case VehicleState.Entering:
                case VehicleState.Navigating:
                case VehicleState.Departing:
                case VehicleState.Exiting:
                    FollowPath();
                    break;
            }
        }

        private void FollowPath()
        {
            if (currentPath == null || currentPathIndex >= currentPath.Count) return;

            var targetNode = currentPath[currentPathIndex];
            if (targetNode == null)
            {
                currentPathIndex++;
                return;
            }

            Vector3 targetPos = targetNode.transform.position;
            Vector3 direction = targetPos - transform.position;
            direction.y = 0f;

            if (direction.sqrMagnitude > 0.01f)
            {
                Quaternion targetRot = Quaternion.LookRotation(direction);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRot, Time.deltaTime * rotationSpeed);
            }

            transform.position = Vector3.MoveTowards(transform.position, targetPos, moveSpeed * Time.deltaTime);

            float dist = Vector3.Distance(transform.position, targetPos);
            if (dist < 0.3f)
            {
                currentPathIndex++;
                if (currentPathIndex >= currentPath.Count)
                    OnPathComplete();
            }
        }

        private void OnPathComplete()
        {
            switch (state)
            {
                case VehicleState.ApproachingGate:
                    state = VehicleState.WaitingAtGate;
                    OnReachedGate?.Invoke(this);
                    Debug.Log($"[VehicleController] {plateNumber} reached entry gate");
                    break;

                case VehicleState.Entering:
                    state = VehicleState.Navigating;
                    break;

                case VehicleState.Navigating:
                    state = VehicleState.Parking;
                    StartCoroutine(ParkCoroutine());
                    break;

                case VehicleState.Departing:
                    state = VehicleState.WaitingAtExit;
                    OnReachedExit?.Invoke(this);
                    Debug.Log($"[VehicleController] {plateNumber} reached exit gate");
                    break;

                case VehicleState.Exiting:
                    state = VehicleState.Gone;
                    OnGone?.Invoke(this);
                    Debug.Log($"[VehicleController] {plateNumber} exited, destroying");
                    Destroy(gameObject, 1f);
                    break;
            }
        }

        private IEnumerator ParkCoroutine()
        {
            if (targetSlot == null)
            {
                state = VehicleState.Parked;
                OnParked?.Invoke(this);
                yield break;
            }

            Vector3 slotPos = targetSlot.transform.position;
            slotPos.y = transform.position.y;

            // Rotate to align with slot orientation
            Vector3 slotForward = targetSlot.transform.forward;
            if (slotForward.sqrMagnitude > 0.01f)
            {
                Quaternion slotRot = Quaternion.LookRotation(-slotForward);
                float elapsed = 0f;
                Quaternion startRot = transform.rotation;
                while (elapsed < 0.5f)
                {
                    elapsed += Time.deltaTime;
                    transform.rotation = Quaternion.Slerp(startRot, slotRot, elapsed / 0.5f);
                    yield return null;
                }
            }

            // Move backward into slot
            float parkDuration = 2f;
            float parkElapsed = 0f;
            Vector3 startPos = transform.position;
            while (parkElapsed < parkDuration)
            {
                parkElapsed += Time.deltaTime;
                float t = Mathf.Clamp01(parkElapsed / parkDuration);
                transform.position = Vector3.Lerp(startPos, slotPos, t);
                yield return null;
            }

            transform.position = slotPos;
            state = VehicleState.Parked;
            OnParked?.Invoke(this);
            Debug.Log($"[VehicleController] {plateNumber} parked at {targetSlot.slotCode}");
        }

        private void OnDestroy()
        {
            OnReachedGate = null;
            OnParked = null;
            OnReachedExit = null;
            OnGone = null;
            currentPath = null;
        }
    }
}
