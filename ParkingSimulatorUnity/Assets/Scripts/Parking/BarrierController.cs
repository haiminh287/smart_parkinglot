using System;
using System.Collections;
using UnityEngine;

namespace ParkingSim.Parking
{
    public class BarrierController : MonoBehaviour
    {
        [SerializeField] private Transform barrierArm;
        [SerializeField] private float openAngle = 90f;
        [SerializeField] private float closedAngle = 0f;
        [SerializeField] private float speed = 2f;

        public bool isEntry;

        /// <summary>
        /// Public accessor để ParkingManager wire barrier arm mà không cần reflection.
        /// </summary>
        public Transform Arm
        {
            get => barrierArm;
            set => barrierArm = value;
        }

        private bool isOpen;
        private float targetAngle;
        private bool eventFired = true;

        public event Action OnBarrierOpened;
        public event Action OnBarrierClosed;

        private void Start()
        {
            targetAngle = closedAngle;
            if (barrierArm != null)
            {
                var rot = barrierArm.localEulerAngles;
                rot.x = closedAngle;
                barrierArm.localEulerAngles = rot;
            }
        }

        private void Update()
        {
            if (barrierArm == null) return;

            var currentRot = barrierArm.localEulerAngles;
            float currentAngle = NormalizeAngle(currentRot.x);
            float normalizedTarget = NormalizeAngle(targetAngle);

            if (Mathf.Abs(currentAngle - normalizedTarget) < 1f)
            {
                if (!eventFired)
                {
                    eventFired = true;
                    if (isOpen)
                        OnBarrierOpened?.Invoke();
                    else
                        OnBarrierClosed?.Invoke();
                }
                return;
            }

            float newAngle = Mathf.LerpAngle(currentAngle, normalizedTarget, Time.deltaTime * speed);
            currentRot.x = newAngle;
            barrierArm.localEulerAngles = currentRot;
        }

        public void Open()
        {
            targetAngle = openAngle;
            isOpen = true;
            eventFired = false;
            string type = isEntry ? "entry" : "exit";
            Debug.Log($"[BarrierController] Opening {type} barrier");
        }

        public void Close()
        {
            targetAngle = closedAngle;
            isOpen = false;
            eventFired = false;
            Debug.Log("[BarrierController] Closing barrier");
        }

        public IEnumerator OpenThenClose(float delay = 3f)
        {
            Open();
            yield return new WaitForSeconds(delay);
            Close();
        }

        public bool IsOpen => isOpen;

        private static float NormalizeAngle(float angle)
        {
            while (angle > 180f) angle -= 360f;
            while (angle < -180f) angle += 360f;
            return angle;
        }
    }
}
