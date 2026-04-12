using System.Collections;
using UnityEngine;
using ParkingSim.Vehicle;

namespace ParkingSim.Vehicle
{
    /// <summary>
    /// Enhances vehicle visual appearance: wheel rotation, body sway,
    /// headlights, brake lights, exhaust particles, suspension bob.
    /// Attach to CarPrefab / MotorbikePrefab alongside VehicleController.
    /// </summary>
    [RequireComponent(typeof(VehicleController))]
    public class VehicleVisualEnhancer : MonoBehaviour
    {
        // ─── Wheels ─────────────────────────────────────────────────────────────
        [Header("Wheel Transforms")]
        [SerializeField] private Transform wheelFL;
        [SerializeField] private Transform wheelFR;
        [SerializeField] private Transform wheelBL;
        [SerializeField] private Transform wheelBR;
        [SerializeField] private float wheelDiameter = 0.6f;

        // ─── Lights ─────────────────────────────────────────────────────────────
        [Header("Lights")]
        [SerializeField] private Light headlightLeft;
        [SerializeField] private Light headlightRight;
        [SerializeField] private Renderer brakeLightRenderer;

        // ─── Exhaust ─────────────────────────────────────────────────────────────
        [Header("Exhaust")]
        [SerializeField] private ParticleSystem exhaustParticle;

        // ─── Suspension ──────────────────────────────────────────────────────────
        [Header("Suspension")]
        [SerializeField] private Transform bodyTransform;   // the body mesh root
        [SerializeField] private float suspensionAmplitude = 0.02f;

        // ─── Material Fix ────────────────────────────────────────────────────────
        [Header("Material")]
        [Tooltip("If true, automatically switches all renderers to URP/Lit on Start.")]
        [SerializeField] private bool autoFixUrpMaterials = true;
        [Tooltip("If true, creates basic car geometry when vehicle has no child renderers.")]
        [SerializeField] private bool autoCreateGeometryIfMissing = true;

        private static readonly Color[] carColors = {
            Color.white, Color.black, new Color(0.15f, 0.15f, 0.15f),
            new Color(0.7f, 0.1f, 0.1f), new Color(0.1f, 0.2f, 0.5f),
            new Color(0.3f, 0.3f, 0.3f), new Color(0.8f, 0.75f, 0.6f),
            new Color(0.05f, 0.3f, 0.15f)
        };

        // ─── Private ─────────────────────────────────────────────────────────────
        private VehicleController vc;
        private float wheelCircumference;
        private float currentLean;
        private Vector3 lastPosition;
        private Vector3 bodyBaseLocalPos;

        // brake light URP emission
        private static readonly int EmissionColor = Shader.PropertyToID("_EmissionColor");
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        private Material brakeMaterialInstance;
        private bool brakesOn;

        // headlight pulse
        private float headlightBaseIntensity = 1.5f;
        private float pulseTimer;

        private void Awake()
        {
            vc = GetComponent<VehicleController>();
            wheelCircumference = Mathf.PI * wheelDiameter;

            if (bodyTransform != null)
                bodyBaseLocalPos = bodyTransform.localPosition;
        }

        private void Start()
        {
            if (autoCreateGeometryIfMissing && GetComponentsInChildren<Renderer>().Length == 0)
                CreateBasicCarGeometry();

            if (autoFixUrpMaterials)
                FixUrpMaterials();

            // Clone brake material so we don't affect all cars sharing the same asset
            if (brakeLightRenderer != null)
            {
                brakeMaterialInstance = brakeLightRenderer.material; // creates instance
                brakeMaterialInstance.EnableKeyword("_EMISSION");
                SetBrakeLights(false);
            }

            // Headlights always on
            if (headlightLeft)  headlightLeft.intensity  = headlightBaseIntensity;
            if (headlightRight) headlightRight.intensity = headlightBaseIntensity;

            lastPosition = transform.position;
        }

        private void Update()
        {
            float speed = GetCurrentSpeed();

            RotateWheels(speed);
            SwayBody(speed);
            HandleExhaust(speed);
            SuspensionBob(speed);
            PulseHeadlights();
            HandleBrakeLights(speed);
        }

        // ─── Speed ───────────────────────────────────────────────────────────────

        private float GetCurrentSpeed()
        {
            // VehicleController moves via MoveTowards — approximate speed from delta pos
            float dist = Vector3.Distance(transform.position, lastPosition);
            float s = dist / Mathf.Max(Time.deltaTime, 0.0001f);
            lastPosition = transform.position;
            return s;
        }

        // ─── Wheel Rotation ───────────────────────────────────────────────────────

        private void RotateWheels(float speed)
        {
            if (wheelCircumference <= 0f) return;

            float rpm      = (speed / wheelCircumference) * 60f;
            float degreesPerSecond = rpm * 6f; // 360° / 60s
            float rotDelta = degreesPerSecond * Time.deltaTime;

            if (wheelFL) wheelFL.Rotate(rotDelta, 0f, 0f, Space.Self);
            if (wheelFR) wheelFR.Rotate(rotDelta, 0f, 0f, Space.Self);
            if (wheelBL) wheelBL.Rotate(rotDelta, 0f, 0f, Space.Self);
            if (wheelBR) wheelBR.Rotate(rotDelta, 0f, 0f, Space.Self);
        }

        // ─── Body Sway ───────────────────────────────────────────────────────────

        private void SwayBody(float speed)
        {
            if (bodyTransform == null) return;

            // turn rate from angular y delta
            float turnRate = 0f;
            if (speed > 0.5f)
            {
                float angY = transform.eulerAngles.y;
                // Angular delta approximation — track previous y
                turnRate = angY; // simplified; real impl stores prevAngY
            }

            float targetLean = -turnRate * 0.05f;
            targetLean = Mathf.Clamp(targetLean, -3f, 3f);
            currentLean = Mathf.LerpAngle(currentLean, targetLean, Time.deltaTime * 5f);

            var angles = bodyTransform.localEulerAngles;
            angles.z = currentLean;
            bodyTransform.localEulerAngles = angles;
        }

        // ─── Exhaust ─────────────────────────────────────────────────────────────

        private void HandleExhaust(float speed)
        {
            if (exhaustParticle == null) return;

            if (speed > 0.5f && !exhaustParticle.isPlaying)
                exhaustParticle.Play();
            else if (speed <= 0.5f && exhaustParticle.isPlaying)
                exhaustParticle.Stop();

            var em = exhaustParticle.emission;
            em.rateOverTime = Mathf.Lerp(3f, 15f, speed / 10f);
        }

        // ─── Suspension Bob ───────────────────────────────────────────────────────

        private void SuspensionBob(float speed)
        {
            if (bodyTransform == null) return;

            float frequency = speed * 2f;
            float offset    = suspensionAmplitude * Mathf.Sin(Time.time * frequency);
            bodyTransform.localPosition = bodyBaseLocalPos + new Vector3(0f, offset, 0f);
        }

        // ─── Headlight Pulse ──────────────────────────────────────────────────────

        private void PulseHeadlights()
        {
            pulseTimer += Time.deltaTime;
            float pulse = 1f + 0.05f * Mathf.Sin(pulseTimer * 1.5f);

            if (headlightLeft)  headlightLeft.intensity  = headlightBaseIntensity * pulse;
            if (headlightRight) headlightRight.intensity = headlightBaseIntensity * pulse;
        }

        // ─── Brake Lights ─────────────────────────────────────────────────────────

        private void HandleBrakeLights(float speed)
        {
            bool shouldBrake = (speed < 0.2f) &&
                               (vc.state == VehicleController.VehicleState.WaitingAtGate ||
                                vc.state == VehicleController.VehicleState.Parking ||
                                vc.state == VehicleController.VehicleState.WaitingAtExit);

            if (shouldBrake != brakesOn)
                SetBrakeLights(shouldBrake);
        }

        private void SetBrakeLights(bool on)
        {
            brakesOn = on;
            if (brakeMaterialInstance == null) return;

            Color emissive = on ? Color.red * 2f : Color.black;
            brakeMaterialInstance.SetColor(EmissionColor, emissive);
        }

        // ─── Auto Create Geometry ─────────────────────────────────────────────────

        private void CreateBasicCarGeometry()
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            Color bodyColor = carColors[Random.Range(0, carColors.Length)];
            Color cabinColor = bodyColor * 0.75f;
            cabinColor.a = 1f;

            // Body
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "Body";
            body.transform.SetParent(transform);
            body.transform.localPosition = new Vector3(0f, 0.4f, 0f);
            body.transform.localScale = new Vector3(2.2f, 0.8f, 4.5f);
            body.transform.localRotation = Quaternion.identity;
            var bodyMat = new Material(shader);
            bodyMat.SetColor(BaseColor, bodyColor);
            bodyMat.color = bodyColor;
            if (bodyMat.HasProperty("_Metallic")) bodyMat.SetFloat("_Metallic", 0.35f);
            if (bodyMat.HasProperty("_Smoothness")) bodyMat.SetFloat("_Smoothness", 0.65f);
            body.GetComponent<Renderer>().material = bodyMat;
            bodyTransform = body.transform;

            // Cabin
            var cabin = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cabin.name = "Cabin";
            cabin.transform.SetParent(transform);
            cabin.transform.localPosition = new Vector3(0f, 1.0f, 0f);
            cabin.transform.localScale = new Vector3(1.8f, 0.6f, 2.0f);
            cabin.transform.localRotation = Quaternion.identity;
            var cabinMat = new Material(shader);
            cabinMat.SetColor(BaseColor, cabinColor);
            cabinMat.color = cabinColor;
            cabin.GetComponent<Renderer>().material = cabinMat;

            // Wheels
            wheelFL = CreateWheel("WheelFL", new Vector3(-1.0f, 0.15f, 1.5f), shader);
            wheelFR = CreateWheel("WheelFR", new Vector3(1.0f, 0.15f, 1.5f), shader);
            wheelBL = CreateWheel("WheelBL", new Vector3(-1.0f, 0.15f, -1.5f), shader);
            wheelBR = CreateWheel("WheelBR", new Vector3(1.0f, 0.15f, -1.5f), shader);

            // Headlights
            var hlLeft = new GameObject("HeadlightLeft");
            hlLeft.transform.SetParent(transform);
            hlLeft.transform.localPosition = new Vector3(-0.7f, 0.5f, 2.3f);
            headlightLeft = hlLeft.AddComponent<Light>();
            headlightLeft.type = LightType.Point;
            headlightLeft.color = new Color(1f, 0.95f, 0.8f);
            headlightLeft.range = 8f;
            headlightLeft.intensity = headlightBaseIntensity;

            var hlRight = new GameObject("HeadlightRight");
            hlRight.transform.SetParent(transform);
            hlRight.transform.localPosition = new Vector3(0.7f, 0.5f, 2.3f);
            headlightRight = hlRight.AddComponent<Light>();
            headlightRight.type = LightType.Point;
            headlightRight.color = new Color(1f, 0.95f, 0.8f);
            headlightRight.range = 8f;
            headlightRight.intensity = headlightBaseIntensity;

            // Brake light
            var brake = GameObject.CreatePrimitive(PrimitiveType.Cube);
            brake.name = "BrakeLight";
            brake.transform.SetParent(transform);
            brake.transform.localPosition = new Vector3(0f, 0.5f, -2.3f);
            brake.transform.localScale = new Vector3(1.6f, 0.15f, 0.05f);
            brake.transform.localRotation = Quaternion.identity;
            var brakeMat = new Material(shader);
            brakeMat.SetColor(BaseColor, Color.red * 0.4f);
            brakeMat.color = Color.red * 0.4f;
            brakeMat.EnableKeyword("_EMISSION");
            brake.GetComponent<Renderer>().material = brakeMat;
            brakeLightRenderer = brake.GetComponent<Renderer>();

            bodyBaseLocalPos = bodyTransform.localPosition;
            Debug.Log($"[VehicleVisualEnhancer] Created basic car geometry for {name}");
        }

        private Transform CreateWheel(string wheelName, Vector3 localPos, Shader shader)
        {
            var wheel = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            wheel.name = wheelName;
            wheel.transform.SetParent(transform);
            wheel.transform.localPosition = localPos;
            wheel.transform.localScale = new Vector3(0.55f, 0.1f, 0.55f);
            wheel.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            var wheelMat = new Material(shader);
            wheelMat.SetColor(BaseColor, new Color(0.1f, 0.1f, 0.1f));
            wheelMat.color = new Color(0.1f, 0.1f, 0.1f);
            if (wheelMat.HasProperty("_Metallic")) wheelMat.SetFloat("_Metallic", 0.1f);
            if (wheelMat.HasProperty("_Smoothness")) wheelMat.SetFloat("_Smoothness", 0.3f);
            wheel.GetComponent<Renderer>().material = wheelMat;
            return wheel.transform;
        }

        // ─── URP Material Fix ─────────────────────────────────────────────────────

        private void FixUrpMaterials()
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
            {
                Debug.LogWarning("[VehicleVisualEnhancer] URP/Lit shader not found — " +
                                 "make sure URP package is installed.");
                return;
            }

            var renderers = GetComponentsInChildren<Renderer>(includeInactive: true);
            int fixed_ = 0;
            foreach (var r in renderers)
            {
                if (r == null) continue;
                // Skip TextMeshPro renderers — they use SDF shader, not URP/Lit
                if (r.GetComponent<TMPro.TMP_Text>() != null) continue;
                // Must get materials array, modify instances, then assign back
                var mats = r.materials;
                bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    var mat = mats[i];
                    if (mat == null) continue;
                    if (mat.shader != null && mat.shader.name.Contains("Universal Render Pipeline"))
                    {
                        // Already URP — but check if it's magenta/pink
                        Color c = mat.HasProperty(BaseColor) ? mat.GetColor(BaseColor) : mat.color;
                        bool isMagenta = c.r > 0.7f && c.b > 0.5f && c.g < 0.3f;
                        if (isMagenta)
                        {
                            Color newCol = carColors[Random.Range(0, carColors.Length)];
                            mat.SetColor(BaseColor, newCol);
                            mat.color = newCol;
                            changed = true;
                            fixed_++;
                        }
                        continue;
                    }

                    Color prevColor = mat.HasProperty(BaseColor) ? mat.GetColor(BaseColor) : mat.color;
                    // Fix magenta/pink (missing shader default) — broader range
                    bool isPink = (prevColor.r > 0.7f && prevColor.b > 0.5f && prevColor.g < 0.3f)
                               || (prevColor.r > 0.9f && prevColor.g < 0.1f && prevColor.b > 0.9f);
                    if (isPink)
                        prevColor = carColors[Random.Range(0, carColors.Length)];

                    mat.shader = shader;
                    mat.SetColor(BaseColor, prevColor);
                    mat.color = prevColor;

                    if (mat.HasProperty("_Metallic"))
                        mat.SetFloat("_Metallic", 0.35f);
                    if (mat.HasProperty("_Smoothness"))
                        mat.SetFloat("_Smoothness", 0.65f);
                    changed = true;
                    fixed_++;
                }
                if (changed) r.materials = mats; // CRITICAL: assign back to take effect
            }
            Debug.Log($"[VehicleVisualEnhancer] Fixed {fixed_} materials to URP/Lit on {name}");
        }

        // ─── Gizmos ───────────────────────────────────────────────────────────────

        private void OnDrawGizmosSelected()
        {
            if (wheelFL) { Gizmos.color = Color.cyan; Gizmos.DrawWireSphere(wheelFL.position, wheelDiameter * 0.5f); }
            if (wheelFR) { Gizmos.color = Color.cyan; Gizmos.DrawWireSphere(wheelFR.position, wheelDiameter * 0.5f); }
        }
    }
}
