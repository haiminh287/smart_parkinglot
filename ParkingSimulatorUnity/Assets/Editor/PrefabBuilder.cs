// PrefabBuilder.cs — Tạo Car và Motorbike prefabs đơn giản từ primitive shapes
// Menu: ParkingSim > Build Vehicle Prefabs

using UnityEngine;
using UnityEditor;

namespace ParkingSim.Editor
{
    public static class PrefabBuilder
    {
        [MenuItem("ParkingSim/\ud83d\ude97 Build Vehicle Prefabs", priority = 5)]
        public static void BuildPrefabs() => BuildPrefabs(showDialog: true);

        public static void BuildPrefabs(bool showDialog)
        {
            EnsureFolder("Assets/Prefabs");

            BuildCarPrefab();
            BuildMotorbikePrefab();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            // Wire into ParkingManager if it exists
            WireIntoParkingManager();

            if (showDialog)
            {
                EditorUtility.DisplayDialog("Prefabs Created",
                    "Car and Motorbike prefabs created at Assets/Prefabs/\n\n" +
                    "They have been automatically assigned to ParkingManager.",
                    "OK");
            }

            Debug.Log("[PrefabBuilder] Vehicle prefabs built and assigned.");
        }

        private static void BuildCarPrefab()
        {
            string path = "Assets/Prefabs/CarPrefab.prefab";
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) != null)
            {
                Debug.Log("[PrefabBuilder] CarPrefab already exists, skipping.");
                return;
            }

            var root = new GameObject("Car");

            // Body
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "Body";
            body.transform.SetParent(root.transform);
            body.transform.localPosition = new Vector3(0, 0.45f, 0);
            body.transform.localScale    = new Vector3(1.8f, 0.6f, 3.6f);
            SetPrimitiveColor(body, new Color(0.2f, 0.45f, 0.85f));
            Object.DestroyImmediate(body.GetComponent<BoxCollider>());

            // Roof/cabin
            var cabin = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cabin.name = "Cabin";
            cabin.transform.SetParent(root.transform);
            cabin.transform.localPosition = new Vector3(0, 0.9f, -0.2f);
            cabin.transform.localScale    = new Vector3(1.6f, 0.5f, 2.0f);
            SetPrimitiveColor(cabin, new Color(0.15f, 0.35f, 0.7f));
            Object.DestroyImmediate(cabin.GetComponent<BoxCollider>());

            // Wheels (4)
            AddWheel(root, new Vector3(-1.0f, 0.2f,  1.3f), "WheelFL");
            AddWheel(root, new Vector3( 1.0f, 0.2f,  1.3f), "WheelFR");
            AddWheel(root, new Vector3(-1.0f, 0.2f, -1.3f), "WheelBL");
            AddWheel(root, new Vector3( 1.0f, 0.2f, -1.3f), "WheelBR");

            // Headlights
            AddLight(root, new Vector3(-0.55f, 0.45f,  1.82f), Color.white,  "HeadlightL");
            AddLight(root, new Vector3( 0.55f, 0.45f,  1.82f), Color.white,  "HeadlightR");
            AddLight(root, new Vector3(-0.55f, 0.45f, -1.82f), Color.red,    "TailLightL");
            AddLight(root, new Vector3( 0.55f, 0.45f, -1.82f), Color.red,    "TailLightR");

            // Add VehicleController
            root.AddComponent<ParkingSim.Vehicle.VehicleController>();

            SavePrefab(root, path);
            Object.DestroyImmediate(root);
        }

        private static void BuildMotorbikePrefab()
        {
            string path = "Assets/Prefabs/MotorbikePrefab.prefab";
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) != null)
            {
                Debug.Log("[PrefabBuilder] MotorbikePrefab already exists, skipping.");
                return;
            }

            var root = new GameObject("Motorbike");

            // Body frame
            var frame = GameObject.CreatePrimitive(PrimitiveType.Cube);
            frame.name = "Frame";
            frame.transform.SetParent(root.transform);
            frame.transform.localPosition = new Vector3(0, 0.55f, 0);
            frame.transform.localScale    = new Vector3(0.5f, 0.4f, 1.8f);
            SetPrimitiveColor(frame, new Color(0.85f, 0.3f, 0.1f));
            Object.DestroyImmediate(frame.GetComponent<BoxCollider>());

            // Fairings (upper body)
            var fairing = GameObject.CreatePrimitive(PrimitiveType.Cube);
            fairing.name = "Fairing";
            fairing.transform.SetParent(root.transform);
            fairing.transform.localPosition = new Vector3(0, 0.85f, 0.1f);
            fairing.transform.localScale    = new Vector3(0.45f, 0.35f, 1.2f);
            SetPrimitiveColor(fairing, new Color(1f, 0.45f, 0.1f));
            Object.DestroyImmediate(fairing.GetComponent<BoxCollider>());

            // Wheels (2 — use cylinders)
            AddMotorbikeWheel(root, new Vector3(0, 0.28f,  0.75f), "WheelFront");
            AddMotorbikeWheel(root, new Vector3(0, 0.28f, -0.75f), "WheelBack");

            // Headlight
            AddLight(root, new Vector3(0, 0.65f, 0.92f), Color.white, "Headlight");

            // Add VehicleController
            root.AddComponent<ParkingSim.Vehicle.VehicleController>();

            SavePrefab(root, path);
            Object.DestroyImmediate(root);
        }

        public static void WireIntoParkingManager()
        {
            var pm = Object.FindObjectOfType<ParkingSim.Core.ParkingManager>();
            if (pm == null) { Debug.Log("[PrefabBuilder] ParkingManager not in scene — skipping auto-wire."); return; }

            var carPrefab  = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/CarPrefab.prefab");
            var motoPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/MotorbikePrefab.prefab");

            var so = new SerializedObject(pm);
            var carProp = so.FindProperty("carPrefab");
            var motoProp = so.FindProperty("motorbikePrefab");
            if (carProp != null && carPrefab != null) carProp.objectReferenceValue = carPrefab;
            if (motoProp != null && motoPrefab != null) motoProp.objectReferenceValue = motoPrefab;
            so.ApplyModifiedPropertiesWithoutUndo();
            Debug.Log("[PrefabBuilder] Wired carPrefab + motorbikePrefab into ParkingManager.");
        }

        // ─── Helpers ───────────────────────────────────────

        private static void AddWheel(GameObject parent, Vector3 pos, string name)
        {
            var wheel = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            wheel.name = name;
            wheel.transform.SetParent(parent.transform);
            wheel.transform.localPosition = pos;
            wheel.transform.localEulerAngles = new Vector3(0, 0, 90);
            wheel.transform.localScale = new Vector3(0.4f, 0.18f, 0.4f);
            SetPrimitiveColor(wheel, new Color(0.15f, 0.15f, 0.15f));
            Object.DestroyImmediate(wheel.GetComponent<CapsuleCollider>());
        }

        private static void AddMotorbikeWheel(GameObject parent, Vector3 pos, string name)
        {
            var wheel = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            wheel.name = name;
            wheel.transform.SetParent(parent.transform);
            wheel.transform.localPosition = pos;
            wheel.transform.localEulerAngles = new Vector3(0, 0, 90);
            wheel.transform.localScale = new Vector3(0.28f, 0.1f, 0.28f);
            SetPrimitiveColor(wheel, new Color(0.12f, 0.12f, 0.12f));
            Object.DestroyImmediate(wheel.GetComponent<CapsuleCollider>());
        }

        private static void AddLight(GameObject parent, Vector3 pos, Color color, string name)
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.name = name;
            cube.transform.SetParent(parent.transform);
            cube.transform.localPosition = pos;
            cube.transform.localScale = new Vector3(0.22f, 0.12f, 0.05f);
            SetPrimitiveColor(cube, color);
            Object.DestroyImmediate(cube.GetComponent<BoxCollider>());
        }

        private static void SetPrimitiveColor(GameObject go, Color color)
        {
            var rend = go.GetComponent<Renderer>();
            if (rend == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            if (shader == null) return;
            rend.sharedMaterial = new Material(shader) { color = color };
        }

        private static void SavePrefab(GameObject go, string path)
        {
            PrefabUtility.SaveAsPrefabAsset(go, path);
            Debug.Log($"[PrefabBuilder] Saved prefab: {path}");
        }

        private static void EnsureFolder(string folder)
        {
            if (!AssetDatabase.IsValidFolder(folder))
            {
                var parts = folder.Split('/');
                string current = parts[0];
                for (int i = 1; i < parts.Length; i++)
                {
                    string next = current + "/" + parts[i];
                    if (!AssetDatabase.IsValidFolder(next))
                        AssetDatabase.CreateFolder(current, parts[i]);
                    current = next;
                }
            }
        }
    }

    // Extension method needed for SerializedProperty.SetValue (shorthand)
    internal static class SerializedPropertyExtensions
    {
        internal static void SetValue(this SerializedProperty prop, Object value)
        {
            if (prop != null) prop.objectReferenceValue = value;
        }
    }
}
