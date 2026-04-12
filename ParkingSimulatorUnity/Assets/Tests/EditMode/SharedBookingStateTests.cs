using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using ParkingSim.API;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class SharedBookingStateTests
    {
        private GameObject stateGo;
        private SharedBookingState bookingState;

        [SetUp]
        public void SetUp()
        {
            // Reset singleton before each test
            ResetSingleton();

            stateGo = new GameObject("SharedBookingState");
            bookingState = stateGo.AddComponent<SharedBookingState>();
        }

        [TearDown]
        public void TearDown()
        {
            if (stateGo != null)
                Object.DestroyImmediate(stateGo);

            ResetSingleton();
        }

        [Test]
        public void should_add_booking_and_retrieve_by_plate()
        {
            // Arrange
            var response = BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car");

            // Act
            bookingState.AddBooking(response);
            var found = bookingState.GetBookingByPlate("51A-224.56");

            // Assert
            Assert.IsNotNull(found);
            Assert.AreEqual("booking-001", found.BookingId);
            Assert.AreEqual("51A-224.56", found.LicensePlate);
            Assert.AreEqual("A-01", found.SlotCode);
            Assert.AreEqual("Car", found.VehicleType);
            Assert.AreEqual("not_checked_in", found.CheckInStatus);
        }

        [Test]
        public void should_return_null_for_nonexistent_plate()
        {
            // Arrange — empty state, no bookings added

            // Act
            var result = bookingState.GetBookingByPlate("99Z-999.99");

            // Assert
            Assert.IsNull(result);
        }

        [Test]
        public void should_retrieve_by_plate_case_insensitively()
        {
            // Arrange
            var response = BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car");
            bookingState.AddBooking(response);

            // Act — query with different casing
            var found = bookingState.GetBookingByPlate("51a-224.56");

            // Assert
            Assert.IsNotNull(found);
            Assert.AreEqual("booking-001", found.BookingId);
        }

        [Test]
        public void should_fire_OnBookingAdded_event()
        {
            // Arrange
            ActiveBooking receivedBooking = null;
            bookingState.OnBookingAdded += booking => receivedBooking = booking;

            var response = BuildBookingResponse("booking-002", "30H-567.89", "A-03", "Car");

            // Act
            bookingState.AddBooking(response);

            // Assert
            Assert.IsNotNull(receivedBooking, "OnBookingAdded event should have fired");
            Assert.AreEqual("booking-002", receivedBooking.BookingId);
            Assert.AreEqual("30H-567.89", receivedBooking.LicensePlate);
        }

        [Test]
        public void should_not_fire_event_when_adding_duplicate_booking()
        {
            // Arrange
            var response = BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car");
            bookingState.AddBooking(response);

            int eventCount = 0;
            bookingState.OnBookingAdded += _ => eventCount++;

            // Act — add same booking again
            bookingState.AddBooking(response);

            // Assert — event should NOT fire for duplicate
            Assert.AreEqual(0, eventCount, "Should not fire event for duplicate booking");
            Assert.AreEqual(1, bookingState.GetActiveBookings().Count);
        }

        [Test]
        public void should_remove_booking_and_fire_event()
        {
            // Arrange
            var response = BuildBookingResponse("booking-003", "59P1-123.45", "M-01", "Motorbike");
            bookingState.AddBooking(response);

            string removedId = null;
            bookingState.OnBookingRemoved += id => removedId = id;

            // Act
            bookingState.RemoveBooking("booking-003");

            // Assert
            Assert.AreEqual("booking-003", removedId, "OnBookingRemoved event should fire with correct ID");
            Assert.IsNull(bookingState.GetBookingById("booking-003"),
                "Booking should be gone after removal");
            Assert.AreEqual(0, bookingState.GetActiveBookings().Count);
        }

        [Test]
        public void should_not_fire_remove_event_for_nonexistent_booking()
        {
            // Arrange
            string removedId = null;
            bookingState.OnBookingRemoved += id => removedId = id;

            // Act
            bookingState.RemoveBooking("nonexistent-id");

            // Assert
            Assert.IsNull(removedId, "Should not fire event when removing nonexistent booking");
        }

        [Test]
        public void should_get_active_bookings_for_dropdown()
        {
            // Arrange
            bookingState.AddBooking(BuildBookingResponse("abcdef01-0000-0000-0000-000000000001",
                "51A-224.56", "A-01", "Car"));
            bookingState.AddBooking(BuildBookingResponse("12345678-0000-0000-0000-000000000002",
                "30H-567.89", "A-03", "Car"));

            // Act
            var dropdown = bookingState.GetActiveBookingsForDropdown();

            // Assert
            Assert.AreEqual(2, dropdown.Count);

            // Label format: "{plate} → {slotCode} ({shortId})"
            Assert.IsTrue(dropdown[0].label.Contains("51A-224.56"), "Label should contain plate");
            Assert.IsTrue(dropdown[0].label.Contains("A-01"), "Label should contain slot code");
            Assert.IsTrue(dropdown[0].label.Contains("abcdef01"), "Label should contain short booking ID");

            Assert.IsNotNull(dropdown[0].booking);
            Assert.IsNotNull(dropdown[1].booking);
        }

        [Test]
        public void should_update_booking_status()
        {
            // Arrange
            bookingState.AddBooking(BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car"));

            // Act
            bookingState.UpdateStatus("booking-001", "checked_in");

            // Assert
            var booking = bookingState.GetBookingById("booking-001");
            Assert.AreEqual("checked_in", booking.CheckInStatus);
        }

        [Test]
        public void should_get_not_checked_in_bookings()
        {
            // Arrange
            bookingState.AddBooking(BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car"));
            bookingState.AddBooking(BuildBookingResponse("booking-002", "30H-567.89", "A-03", "Car"));
            bookingState.UpdateStatus("booking-001", "checked_in");

            // Act
            var notCheckedIn = bookingState.GetNotCheckedIn();

            // Assert — only booking-002 is not_checked_in
            Assert.AreEqual(1, notCheckedIn.Count);
            Assert.AreEqual("booking-002", notCheckedIn[0].BookingId);
        }

        [Test]
        public void should_clear_all_bookings()
        {
            // Arrange
            bookingState.AddBooking(BuildBookingResponse("booking-001", "51A-224.56", "A-01", "Car"));
            bookingState.AddBooking(BuildBookingResponse("booking-002", "30H-567.89", "A-03", "Car"));

            // Act
            bookingState.Clear();

            // Assert
            Assert.AreEqual(0, bookingState.GetActiveBookings().Count);
            Assert.IsNull(bookingState.GetBookingByPlate("51A-224.56"));
        }

        [Test]
        public void should_not_add_booking_when_response_is_null()
        {
            // Arrange + Act
            bookingState.AddBooking(null);

            // Assert
            Assert.AreEqual(0, bookingState.GetActiveBookings().Count);
        }

        [Test]
        public void should_not_add_booking_when_booking_data_is_null()
        {
            // Arrange
            var response = new BookingCreateResponse { Booking = null, QrCode = "qr" };

            // Act
            bookingState.AddBooking(response);

            // Assert
            Assert.AreEqual(0, bookingState.GetActiveBookings().Count);
        }

        // ─── Helpers ─────────────────────────────────────────

        private static BookingCreateResponse BuildBookingResponse(
            string bookingId, string plate, string slotCode, string vehicleType)
        {
            return new BookingCreateResponse
            {
                Booking = new BookingData
                {
                    Id = bookingId,
                    Vehicle = new BookingVehicleInfo
                    {
                        Id = "vehicle-" + plate,
                        LicensePlate = plate,
                        VehicleType = vehicleType,
                        Name = plate
                    },
                    CarSlot = new BookingSlotInfo
                    {
                        Id = "slot-" + slotCode,
                        ZoneId = "zone-001",
                        Code = slotCode,
                        IsAvailable = false
                    }
                },
                QrCode = "{\"booking_id\":\"" + bookingId + "\"}"
            };
        }

        private static void ResetSingleton()
        {
            var prop = typeof(SharedBookingState).GetProperty("Instance",
                BindingFlags.Public | BindingFlags.Static);
            if (prop != null)
            {
                var setter = prop.GetSetMethod(true);
                setter?.Invoke(null, new object[] { null });
            }
        }
    }
}
