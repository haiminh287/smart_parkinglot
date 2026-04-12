using UnityEngine;
using TMPro;

namespace ParkingSim.Parking
{
    public class ParkingSlot : MonoBehaviour
    {
        public enum SlotType { Painted, Garage, Motorbike }
        public enum SlotStatus { Available, Reserved, Occupied, Maintenance }

        [Header("Identity")]
        public string slotId;
        public string slotCode;
        public SlotType slotType;
        public string vehicleType;

        [Header("State")]
        public SlotStatus status = SlotStatus.Available;
        public string assignedPlate;
        public string assignedBookingId;

        private Renderer slotRenderer;
        private Material slotMaterial;
        private TextMeshPro labelText;
        private Color targetColor;
        private Color currentColor;

        private void Awake()
        {
            slotRenderer = GetComponentInChildren<Renderer>();
            if (slotRenderer != null)
            {
                slotMaterial = slotRenderer.material;
                currentColor = StatusToColor(SlotStatus.Available);
                targetColor = currentColor;
                ApplyColor(currentColor);
            }

            labelText = GetComponentInChildren<TextMeshPro>();
        }

        private void Update()
        {
            if (slotMaterial == null) return;

            currentColor = Color.Lerp(currentColor, targetColor, Time.deltaTime * 2f);
            ApplyColor(currentColor);
        }

        public void Initialize(string code, string vType)
        {
            slotCode = code;
            vehicleType = vType;
            slotType = InferSlotType(code, vType);
            targetColor = StatusToColor(status);
            currentColor = targetColor;
            if (slotMaterial != null) ApplyColor(currentColor);
            UpdateLabel();
        }

        public void UpdateState(SlotStatus newStatus, string plate = null, string bookingId = null)
        {
            status = newStatus;
            assignedPlate = plate;
            assignedBookingId = bookingId;
            targetColor = StatusToColor(newStatus);
            UpdateLabel();
        }

        private void UpdateLabel()
        {
            if (labelText == null) return;
            labelText.text = string.IsNullOrEmpty(assignedPlate)
                ? slotCode
                : $"{slotCode}\n{assignedPlate}";
        }

        private void ApplyColor(Color color)
        {
            if (slotMaterial == null) return;
            color.a = 0.35f;
            slotMaterial.SetColor("_BaseColor", color);
            slotMaterial.color = color;
        }

        public static SlotType InferSlotType(string code, string vType)
        {
            if (!string.IsNullOrEmpty(vType) && vType.ToLower() == "motorbike")
                return SlotType.Motorbike;
            if (!string.IsNullOrEmpty(code) && code.StartsWith("G"))
                return SlotType.Garage;
            return SlotType.Painted;
        }

        public static Color StatusToColor(SlotStatus s)
        {
            switch (s)
            {
                case SlotStatus.Available:   return new Color(0.2f, 0.8f, 0.2f);
                case SlotStatus.Reserved:    return new Color(1f, 0.85f, 0f);
                case SlotStatus.Occupied:    return new Color(0.9f, 0.15f, 0.15f);
                case SlotStatus.Maintenance: return new Color(0.5f, 0.5f, 0.5f);
                default:                     return Color.white;
            }
        }

        public static SlotStatus ParseStatus(string apiStatus)
        {
            if (string.IsNullOrEmpty(apiStatus)) return SlotStatus.Available;
            switch (apiStatus.ToLower())
            {
                case "available":   return SlotStatus.Available;
                case "reserved":    return SlotStatus.Reserved;
                case "occupied":    return SlotStatus.Occupied;
                case "maintenance": return SlotStatus.Maintenance;
                default:            return SlotStatus.Available;
            }
        }
    }
}
