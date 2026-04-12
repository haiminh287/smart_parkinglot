using System;
using UnityEngine;
using ParkingSim.Parking;

namespace ParkingSim.Core
{
    public class FloorVisibilityManager : MonoBehaviour
    {
        [SerializeField] private ParkingLotGenerator generator;

        private int currentFloor;
        private int totalFloors;

        public int CurrentFloor => currentFloor;
        public event Action<int> OnFloorChanged;

        private void Start()
        {
            totalFloors = generator.numberOfFloors;
        }

        public void ShowFloor(int floorIndex)
        {
            for (int i = 0; i < totalFloors; i++)
            {
                var floor = generator.transform.Find($"Floor_{i + 1}");
                if (floor != null) floor.gameObject.SetActive(i == floorIndex);
            }
            currentFloor = floorIndex;
            OnFloorChanged?.Invoke(currentFloor);
            Debug.Log($"[FloorVisibilityManager] Showing floor {floorIndex + 1}");
        }

        public void ShowAllFloors()
        {
            for (int i = 0; i < totalFloors; i++)
            {
                var floor = generator.transform.Find($"Floor_{i + 1}");
                if (floor != null) floor.gameObject.SetActive(true);
            }
            Debug.Log("[FloorVisibilityManager] Showing all floors");
        }

        public void NextFloor()
        {
            ShowFloor((currentFloor + 1) % totalFloors);
        }

        public void PrevFloor()
        {
            ShowFloor((currentFloor - 1 + totalFloors) % totalFloors);
        }

        public void ToggleFloorTransparency(int floorIndex, float alpha)
        {
            var floor = generator.transform.Find($"Floor_{floorIndex + 1}");
            if (floor == null) return;

            var renderers = floor.GetComponentsInChildren<Renderer>();
            foreach (var rend in renderers)
            {
                foreach (var mat in rend.materials)
                {
                    mat.SetFloat("_Surface", alpha < 1f ? 1f : 0f); // URP: 0=Opaque, 1=Transparent
                    mat.SetFloat("_Blend", 0f);
                    var color = mat.GetColor("_BaseColor");
                    color.a = alpha;
                    mat.SetColor("_BaseColor", color);

                    if (alpha < 1f)
                    {
                        mat.SetOverrideTag("RenderType", "Transparent");
                        mat.renderQueue = 3000;
                    }
                    else
                    {
                        mat.SetOverrideTag("RenderType", "Opaque");
                        mat.renderQueue = 2000;
                    }
                }
            }
            Debug.Log($"[FloorVisibilityManager] Floor {floorIndex + 1} alpha={alpha:F2}");
        }
    }
}
