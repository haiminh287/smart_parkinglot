using UnityEngine;
using TMPro;

namespace ParkingSim.Vehicle
{
    /// <summary>
    /// Static helper to create realistic 3D Vietnamese license plates (rear only).
    /// 2-line format: Line1 = province+series, Line2 = numbers.
    /// White background, black border, black bold text.
    /// Modeled after real VN 2-row plate (20.5cm × 17.5cm) scaled ×3.5 for visibility.
    /// </summary>
    public static class LicensePlateCreator
    {
        // Real VN 2-row plate ≈ 20.5×17.5cm → scaled ×3.5 for sim visibility
        private const float PlateWidth = 0.72f;
        private const float PlateHeight = 0.46f;
        private const float PlateDepth = 0.015f;
        private const float BorderThickness = 0.012f;

        /// <summary>
        /// Creates a rear-only 3D Vietnamese license plate attached to a vehicle.
        /// Container rotated 180° Y so the plate outward face (+Z local) points toward vehicle rear.
        /// Text also rotated 180° Y — TMP front face is -Z, so both rotations needed for correct read direction.
        /// </summary>
        public static GameObject CreateRearPlate(Transform vehicleTransform, string plateText)
        {
            var container = new GameObject("LicensePlate_Rear");
            container.transform.SetParent(vehicleTransform);
            container.transform.localPosition = new Vector3(0f, 0.38f, -2.3f);
            container.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);

            var urpShader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");

            // 1. White background plate
            var bg = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bg.name = "PlateBG";
            bg.transform.SetParent(container.transform);
            bg.transform.localPosition = Vector3.zero;
            bg.transform.localScale = new Vector3(PlateWidth, PlateHeight, PlateDepth);
            bg.transform.localRotation = Quaternion.identity;
            var bgMat = new Material(urpShader) { color = new Color(0.95f, 0.95f, 0.93f) };
            bgMat.SetFloat("_Smoothness", 0.2f);
            bg.GetComponent<Renderer>().sharedMaterial = bgMat;
            RemoveCollider(bg);

            // 2. Black border frame
            float halfW = PlateWidth / 2f;
            float halfH = PlateHeight / 2f;
            float faceZ = 0.01f; // slightly in front of plate surface

            CreateBorderStrip(container.transform, "BorderTop", urpShader,
                new Vector3(0f, halfH, faceZ),
                new Vector3(PlateWidth + BorderThickness * 2f, BorderThickness, BorderThickness));
            CreateBorderStrip(container.transform, "BorderBottom", urpShader,
                new Vector3(0f, -halfH, faceZ),
                new Vector3(PlateWidth + BorderThickness * 2f, BorderThickness, BorderThickness));
            CreateBorderStrip(container.transform, "BorderLeft", urpShader,
                new Vector3(-halfW, 0f, faceZ),
                new Vector3(BorderThickness, PlateHeight, BorderThickness));
            CreateBorderStrip(container.transform, "BorderRight", urpShader,
                new Vector3(halfW, 0f, faceZ),
                new Vector3(BorderThickness, PlateHeight, BorderThickness));

            // Horizontal divider between line 1 and line 2
            CreateBorderStrip(container.transform, "Divider", urpShader,
                new Vector3(0f, 0f, faceZ),
                new Vector3(PlateWidth * 0.85f, BorderThickness * 0.6f, BorderThickness));

            // 3. Parse plate text into 2 lines
            string line1Text = plateText;
            string line2Text = "";
            int dashIndex = plateText.IndexOf('-');
            if (dashIndex >= 0)
            {
                line1Text = plateText.Substring(0, dashIndex);
                line2Text = plateText.Substring(dashIndex + 1);
            }

            // Text rect dimensions
            float textW = PlateWidth - 0.08f;   // 0.64
            float textH = PlateHeight * 0.42f;  // 0.193 per line

            // 4. Line 1 (top) — province + series e.g. "51A"
            var line1Go = new GameObject("PlateTextLine1");
            line1Go.transform.SetParent(container.transform);
            line1Go.transform.localPosition = new Vector3(0f, PlateHeight * 0.22f, faceZ + 0.002f);
            line1Go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            var line1Tmp = line1Go.AddComponent<TextMeshPro>();
            line1Tmp.text = line1Text;
            line1Tmp.fontStyle = FontStyles.Bold;
            line1Tmp.color = Color.black;
            line1Tmp.alignment = TextAlignmentOptions.Center;
            line1Tmp.rectTransform.sizeDelta = new Vector2(textW, textH);
            line1Tmp.enableAutoSizing = true;
            line1Tmp.fontSizeMin = 0.5f;
            line1Tmp.fontSizeMax = 3.0f;
            line1Tmp.overflowMode = TextOverflowModes.Truncate;
            line1Tmp.outlineWidth = 0.15f;
            line1Tmp.outlineColor = new Color32(0, 0, 0, 255);

            // 5. Line 2 (bottom) — numbers e.g. "999.88"
            if (!string.IsNullOrEmpty(line2Text))
            {
                var line2Go = new GameObject("PlateTextLine2");
                line2Go.transform.SetParent(container.transform);
                line2Go.transform.localPosition = new Vector3(0f, -PlateHeight * 0.22f, faceZ + 0.002f);
                line2Go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
                var line2Tmp = line2Go.AddComponent<TextMeshPro>();
                line2Tmp.text = line2Text;
                line2Tmp.fontStyle = FontStyles.Bold;
                line2Tmp.color = Color.black;
                line2Tmp.alignment = TextAlignmentOptions.Center;
                line2Tmp.rectTransform.sizeDelta = new Vector2(textW, textH);
                line2Tmp.enableAutoSizing = true;
                line2Tmp.fontSizeMin = 0.5f;
                line2Tmp.fontSizeMax = 3.0f;
                line2Tmp.overflowMode = TextOverflowModes.Truncate;
                line2Tmp.outlineWidth = 0.15f;
                line2Tmp.outlineColor = new Color32(0, 0, 0, 255);
            }

            return container;
        }

        /// <summary>
        /// Updates the text of an existing plate object (both lines).
        /// </summary>
        public static void UpdatePlateText(GameObject plateObject, string newText)
        {
            if (plateObject == null) return;

            string line1Text = newText;
            string line2Text = "";
            int dashIndex = newText.IndexOf('-');
            if (dashIndex >= 0)
            {
                line1Text = newText.Substring(0, dashIndex);
                line2Text = newText.Substring(dashIndex + 1);
            }

            var line1Transform = plateObject.transform.Find("PlateTextLine1");
            if (line1Transform != null)
            {
                var tmp1 = line1Transform.GetComponent<TextMeshPro>();
                if (tmp1 != null) tmp1.text = line1Text;
            }

            var line2Transform = plateObject.transform.Find("PlateTextLine2");
            if (line2Transform != null)
            {
                var tmp2 = line2Transform.GetComponent<TextMeshPro>();
                if (tmp2 != null) tmp2.text = line2Text;
            }
        }

        private static void CreateBorderStrip(Transform parent, string name, Shader shader, Vector3 localPos, Vector3 scale)
        {
            var strip = GameObject.CreatePrimitive(PrimitiveType.Cube);
            strip.name = name;
            strip.transform.SetParent(parent);
            strip.transform.localPosition = localPos;
            strip.transform.localScale = scale;
            strip.transform.localRotation = Quaternion.identity;
            strip.GetComponent<Renderer>().sharedMaterial = new Material(shader) { color = Color.black };
            RemoveCollider(strip);
        }

        private static void RemoveCollider(GameObject go)
        {
            var col = go.GetComponent<Collider>();
            if (col != null) UnityEngine.Object.Destroy(col);
        }
    }
}
