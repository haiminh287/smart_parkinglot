using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using ParkingSim.API;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class MockDataProviderTests
    {
        [Test]
        public void should_generate_correct_number_of_mock_slots()
        {
            // Arrange + Act
            List<SlotData> slots = MockDataProvider.GenerateMockSlots();

            // Assert — 10 painted (A) + 5 garage (G) + 20 motorbike (M) = 35
            Assert.AreEqual(35, slots.Count);

            int paintedCount = slots.Count(s => s.Code.StartsWith("A-"));
            int garageCount = slots.Count(s => s.Code.StartsWith("G-"));
            int motoCount = slots.Count(s => s.Code.StartsWith("M-"));

            Assert.AreEqual(10, paintedCount, "Expected 10 painted slots (A-xx)");
            Assert.AreEqual(5, garageCount, "Expected 5 garage slots (G-xx)");
            Assert.AreEqual(20, motoCount, "Expected 20 motorbike slots (M-xx)");
        }

        [Test]
        public void should_generate_slots_with_valid_status_distribution()
        {
            // Arrange + Act
            List<SlotData> slots = MockDataProvider.GenerateMockSlots();

            // Assert — PickStatus distributes: ~60% available, ~20% occupied, ~15% reserved, ~5% maintenance
            var validStatuses = new HashSet<string> { "available", "occupied", "reserved", "maintenance" };
            foreach (var slot in slots)
            {
                Assert.IsTrue(validStatuses.Contains(slot.Status),
                    $"Slot {slot.Code} has invalid status '{slot.Status}'");
            }

            int availableCount = slots.Count(s => s.Status == "available");
            Assert.Greater(availableCount, 0, "Should have some available slots");

            // IsAvailable should match status == "available"
            foreach (var slot in slots)
            {
                bool expectedAvailable = slot.Status == "available";
                Assert.AreEqual(expectedAvailable, slot.IsAvailable,
                    $"Slot {slot.Code}: IsAvailable={slot.IsAvailable} but status='{slot.Status}'");
            }
        }

        [Test]
        public void should_generate_unique_slot_codes()
        {
            // Arrange + Act
            List<SlotData> slots = MockDataProvider.GenerateMockSlots();

            // Assert — all codes unique
            var codes = slots.Select(s => s.Code).ToList();
            var uniqueCodes = new HashSet<string>(codes);
            Assert.AreEqual(codes.Count, uniqueCodes.Count, "Slot codes must be unique");

            // Also verify IDs are unique
            var ids = slots.Select(s => s.Id).ToList();
            var uniqueIds = new HashSet<string>(ids);
            Assert.AreEqual(ids.Count, uniqueIds.Count, "Slot IDs must be unique");
        }

        [Test]
        public void should_generate_mock_vehicles_with_valid_data()
        {
            // Arrange + Act
            List<VehicleData> vehicles = MockDataProvider.GenerateMockVehicles();

            // Assert
            Assert.AreEqual(3, vehicles.Count, "Expected 3 mock vehicles");

            foreach (var v in vehicles)
            {
                Assert.IsFalse(string.IsNullOrEmpty(v.Id), "Vehicle ID should not be empty");
                Assert.IsFalse(string.IsNullOrEmpty(v.LicensePlate), "LicensePlate should not be empty");
                Assert.IsFalse(string.IsNullOrEmpty(v.VehicleType), "VehicleType should not be empty");
                Assert.IsFalse(string.IsNullOrEmpty(v.Brand), "Brand should not be empty");
                Assert.IsFalse(string.IsNullOrEmpty(v.Model), "Model should not be empty");
                Assert.IsFalse(string.IsNullOrEmpty(v.Color), "Color should not be empty");
                Assert.AreEqual(MockIds.USER_1, v.UserId, "All vehicles belong to USER_1");
            }

            // At least one default vehicle
            Assert.IsTrue(vehicles.Any(v => v.IsDefault), "Should have at least one default vehicle");

            // Valid vehicle types
            var validTypes = new HashSet<string> { "Car", "Motorbike" };
            foreach (var v in vehicles)
            {
                Assert.IsTrue(validTypes.Contains(v.VehicleType),
                    $"Vehicle {v.LicensePlate} has invalid type '{v.VehicleType}'");
            }
        }

        [Test]
        public void should_generate_mock_bookings_with_valid_references()
        {
            // Arrange + Act
            List<BookingData> bookings = MockDataProvider.GenerateMockBookings();
            List<VehicleData> vehicles = MockDataProvider.GenerateMockVehicles();
            List<SlotData> slots = MockDataProvider.GenerateMockSlots();

            // Assert
            Assert.AreEqual(3, bookings.Count, "Expected 3 mock bookings");

            var vehicleIds = new HashSet<string>(vehicles.Select(v => v.Id));
            var slotIds = new HashSet<string>(slots.Select(s => s.Id));

            foreach (var b in bookings)
            {
                Assert.IsFalse(string.IsNullOrEmpty(b.Id), "Booking ID should not be empty");
                Assert.AreEqual(MockIds.USER_1, b.UserId, "All bookings belong to USER_1");
                Assert.IsNotNull(b.Vehicle, $"Booking {b.Id} missing Vehicle");
                Assert.IsNotNull(b.CarSlot, $"Booking {b.Id} missing CarSlot");
                Assert.IsNotNull(b.Zone, $"Booking {b.Id} missing Zone");
                Assert.IsNotNull(b.Floor, $"Booking {b.Id} missing Floor");
                Assert.IsNotNull(b.ParkingLot, $"Booking {b.Id} missing ParkingLot");

                // Vehicle reference exists
                Assert.IsTrue(vehicleIds.Contains(b.Vehicle.Id),
                    $"Booking {b.Id} references unknown vehicle '{b.Vehicle.Id}'");

                // Slot reference exists
                Assert.IsTrue(slotIds.Contains(b.CarSlot.Id),
                    $"Booking {b.Id} references unknown slot '{b.CarSlot.Id}'");

                // Has QR code data
                Assert.IsFalse(string.IsNullOrEmpty(b.QrCodeData),
                    $"Booking {b.Id} missing QR code data");

                // Valid check-in status
                var validStatuses = new HashSet<string> { "checked_in", "not_checked_in", "checked_out" };
                Assert.IsTrue(validStatuses.Contains(b.CheckInStatus),
                    $"Booking {b.Id} has invalid check-in status '{b.CheckInStatus}'");
            }
        }

        [Test]
        public void should_generate_mock_floors_with_zones()
        {
            // Arrange + Act
            List<FloorData> floors = MockDataProvider.GenerateMockFloors();

            // Assert
            Assert.AreEqual(2, floors.Count, "Expected 2 floors");

            foreach (var floor in floors)
            {
                Assert.IsFalse(string.IsNullOrEmpty(floor.Id));
                Assert.AreEqual(MockIds.LOT_1, floor.ParkingLot);
                Assert.IsNotNull(floor.Zones);
                Assert.AreEqual(3, floor.Zones.Count, $"Floor {floor.Name} should have 3 zones");

                foreach (var zone in floor.Zones)
                {
                    Assert.IsFalse(string.IsNullOrEmpty(zone.Id));
                    Assert.AreEqual(floor.Id, zone.Floor);
                    Assert.Greater(zone.Capacity, 0);
                    Assert.GreaterOrEqual(zone.AvailableSlots, 0);
                    Assert.LessOrEqual(zone.AvailableSlots, zone.Capacity);
                }
            }
        }

        [Test]
        public void should_assign_correct_zone_references_to_slots()
        {
            // Arrange + Act
            List<SlotData> slots = MockDataProvider.GenerateMockSlots();

            // Assert — verify zone assignments
            var paintedSlots = slots.Where(s => s.Code.StartsWith("A-")).ToList();
            var garageSlots = slots.Where(s => s.Code.StartsWith("G-")).ToList();
            var motoSlots = slots.Where(s => s.Code.StartsWith("M-")).ToList();

            foreach (var s in paintedSlots)
                Assert.AreEqual(MockIds.ZONE_CAR_PAINTED_F1, s.Zone,
                    $"Painted slot {s.Code} should belong to ZONE_CAR_PAINTED_F1");

            foreach (var s in garageSlots)
                Assert.AreEqual(MockIds.ZONE_CAR_GARAGE_F1, s.Zone,
                    $"Garage slot {s.Code} should belong to ZONE_CAR_GARAGE_F1");

            foreach (var s in motoSlots)
                Assert.AreEqual(MockIds.ZONE_MOTO_F1, s.Zone,
                    $"Moto slot {s.Code} should belong to ZONE_MOTO_F1");
        }
    }
}
