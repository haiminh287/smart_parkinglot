using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using ParkingSim.Parking;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class ParkingSlotTests
    {
        private GameObject slotGo;
        private ParkingSlot slot;

        [SetUp]
        public void SetUp()
        {
            slotGo = new GameObject("TestSlot");
            // Add a child with Renderer so Awake can find it
            var visual = GameObject.CreatePrimitive(PrimitiveType.Cube);
            visual.transform.SetParent(slotGo.transform);
            slot = slotGo.AddComponent<ParkingSlot>();
        }

        [TearDown]
        public void TearDown()
        {
            if (slotGo != null)
                Object.DestroyImmediate(slotGo);
        }

        // ─── InferSlotType (static) ──────────────────────────

        [Test]
        public void should_infer_slot_type_garage_from_G_prefix()
        {
            // Act
            var result = ParkingSlot.InferSlotType("G-01", "Car");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Garage, result);
        }

        [Test]
        public void should_infer_slot_type_garage_from_G_prefix_when_any_vehicle_type()
        {
            // Act — G prefix with non-motorbike type
            var result = ParkingSlot.InferSlotType("G-05", "SUV");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Garage, result);
        }

        [Test]
        public void should_infer_slot_type_motorbike_from_vehicle_type()
        {
            // Act — "motorbike" (case insensitive) overrides code prefix
            var result = ParkingSlot.InferSlotType("M-01", "Motorbike");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Motorbike, result);
        }

        [Test]
        public void should_infer_slot_type_motorbike_case_insensitive()
        {
            // Act
            var result = ParkingSlot.InferSlotType("X-01", "motorbike");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Motorbike, result);
        }

        [Test]
        public void should_infer_slot_type_motorbike_overrides_G_prefix()
        {
            // Motorbike vehicleType takes priority over G prefix
            var result = ParkingSlot.InferSlotType("G-01", "Motorbike");

            // Assert — Motorbike check comes first in InferSlotType
            Assert.AreEqual(ParkingSlot.SlotType.Motorbike, result);
        }

        [Test]
        public void should_infer_slot_type_painted_for_car()
        {
            // Act
            var result = ParkingSlot.InferSlotType("A-01", "Car");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Painted, result);
        }

        [Test]
        public void should_infer_slot_type_painted_for_null_code_and_null_type()
        {
            // Act
            var result = ParkingSlot.InferSlotType(null, null);

            // Assert — defaults to Painted
            Assert.AreEqual(ParkingSlot.SlotType.Painted, result);
        }

        [Test]
        public void should_infer_slot_type_painted_for_empty_strings()
        {
            // Act
            var result = ParkingSlot.InferSlotType("", "");

            // Assert
            Assert.AreEqual(ParkingSlot.SlotType.Painted, result);
        }

        // ─── ParseStatus (static) ───────────────────────────

        [Test]
        public void should_parse_status_strings_correctly()
        {
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, ParkingSlot.ParseStatus("available"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Reserved, ParkingSlot.ParseStatus("reserved"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Occupied, ParkingSlot.ParseStatus("occupied"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Maintenance, ParkingSlot.ParseStatus("maintenance"));
        }

        [Test]
        public void should_parse_status_case_insensitive()
        {
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, ParkingSlot.ParseStatus("Available"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Occupied, ParkingSlot.ParseStatus("OCCUPIED"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Reserved, ParkingSlot.ParseStatus("Reserved"));
            Assert.AreEqual(ParkingSlot.SlotStatus.Maintenance, ParkingSlot.ParseStatus("MAINTENANCE"));
        }

        [Test]
        public void should_parse_null_status_as_available()
        {
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, ParkingSlot.ParseStatus(null));
        }

        [Test]
        public void should_parse_empty_status_as_available()
        {
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, ParkingSlot.ParseStatus(""));
        }

        [Test]
        public void should_parse_unknown_status_as_available()
        {
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, ParkingSlot.ParseStatus("invalid_status"));
        }

        // ─── StatusToColor (static) ─────────────────────────

        [Test]
        public void should_return_distinct_colors_for_each_status()
        {
            var available = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Available);
            var reserved = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Reserved);
            var occupied = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Occupied);
            var maintenance = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Maintenance);

            Assert.AreNotEqual(available, reserved);
            Assert.AreNotEqual(available, occupied);
            Assert.AreNotEqual(available, maintenance);
            Assert.AreNotEqual(reserved, occupied);
            Assert.AreNotEqual(reserved, maintenance);
            Assert.AreNotEqual(occupied, maintenance);
        }

        [Test]
        public void should_return_green_color_for_available()
        {
            var color = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Available);

            // Expected: new Color(0.2f, 0.8f, 0.2f)
            Assert.AreEqual(0.2f, color.r, 0.01f);
            Assert.AreEqual(0.8f, color.g, 0.01f);
            Assert.AreEqual(0.2f, color.b, 0.01f);
        }

        [Test]
        public void should_return_red_color_for_occupied()
        {
            var color = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Occupied);

            // Expected: new Color(0.9f, 0.15f, 0.15f)
            Assert.AreEqual(0.9f, color.r, 0.01f);
            Assert.AreEqual(0.15f, color.g, 0.01f);
            Assert.AreEqual(0.15f, color.b, 0.01f);
        }

        // ─── UpdateState (instance) ─────────────────────────

        [Test]
        public void should_update_state_and_target_color()
        {
            // Arrange
            slot.Initialize("A-01", "Car");
            Assert.AreEqual(ParkingSlot.SlotStatus.Available, slot.status, "Precondition: starts Available");

            // Act
            slot.UpdateState(ParkingSlot.SlotStatus.Occupied, "51A-224.56", "booking-001");

            // Assert — public state
            Assert.AreEqual(ParkingSlot.SlotStatus.Occupied, slot.status);
            Assert.AreEqual("51A-224.56", slot.assignedPlate);
            Assert.AreEqual("booking-001", slot.assignedBookingId);

            // Assert — targetColor set via reflection
            var targetColorField = typeof(ParkingSlot).GetField("targetColor",
                BindingFlags.NonPublic | BindingFlags.Instance);
            Assert.IsNotNull(targetColorField, "targetColor field should exist");

            Color targetColor = (Color)targetColorField.GetValue(slot);
            Color expectedColor = ParkingSlot.StatusToColor(ParkingSlot.SlotStatus.Occupied);
            Assert.AreEqual(expectedColor.r, targetColor.r, 0.01f);
            Assert.AreEqual(expectedColor.g, targetColor.g, 0.01f);
            Assert.AreEqual(expectedColor.b, targetColor.b, 0.01f);
        }

        [Test]
        public void should_update_state_to_maintenance()
        {
            // Arrange
            slot.Initialize("G-01", "Car");

            // Act
            slot.UpdateState(ParkingSlot.SlotStatus.Maintenance);

            // Assert
            Assert.AreEqual(ParkingSlot.SlotStatus.Maintenance, slot.status);
            Assert.IsNull(slot.assignedPlate);
            Assert.IsNull(slot.assignedBookingId);
        }

        // ─── Initialize (instance) ──────────────────────────

        [Test]
        public void should_initialize_with_code_and_vehicle_type()
        {
            // Act
            slot.Initialize("G-03", "Car");

            // Assert
            Assert.AreEqual("G-03", slot.slotCode);
            Assert.AreEqual("Car", slot.vehicleType);
            Assert.AreEqual(ParkingSlot.SlotType.Garage, slot.slotType);
        }

        [Test]
        public void should_initialize_motorbike_slot()
        {
            // Act
            slot.Initialize("M-15", "Motorbike");

            // Assert
            Assert.AreEqual("M-15", slot.slotCode);
            Assert.AreEqual("Motorbike", slot.vehicleType);
            Assert.AreEqual(ParkingSlot.SlotType.Motorbike, slot.slotType);
        }

        [Test]
        public void should_initialize_painted_slot()
        {
            // Act
            slot.Initialize("A-07", "Car");

            // Assert
            Assert.AreEqual("A-07", slot.slotCode);
            Assert.AreEqual(ParkingSlot.SlotType.Painted, slot.slotType);
        }
    }
}
