using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using ParkingSim.API;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class DataModelsTests
    {
        [Test]
        public void should_serialize_BookingCreateRequest_with_correct_json_properties()
        {
            // Arrange
            var request = new BookingCreateRequest
            {
                VehicleId = "vehicle-001",
                SlotId = "slot-001",
                ZoneId = "zone-001",
                ParkingLotId = "lot-001",
                StartTime = "2026-04-01T10:00:00Z",
                EndTime = "2026-04-01T12:00:00Z",
                PackageType = "hourly",
                PaymentMethod = "on_exit"
            };

            // Act
            string json = JsonConvert.SerializeObject(request);
            var parsed = JObject.Parse(json);

            // Assert — verify JSON property names match [JsonProperty] attributes
            Assert.IsNotNull(parsed["vehicleId"], "Missing 'vehicleId' property");
            Assert.IsNotNull(parsed["slotId"], "Missing 'slotId' property");
            Assert.IsNotNull(parsed["zoneId"], "Missing 'zoneId' property");
            Assert.IsNotNull(parsed["parkingLotId"], "Missing 'parkingLotId' property");
            Assert.IsNotNull(parsed["startTime"], "Missing 'startTime' property");
            Assert.IsNotNull(parsed["endTime"], "Missing 'endTime' property");
            Assert.IsNotNull(parsed["packageType"], "Missing 'packageType' property");
            Assert.IsNotNull(parsed["paymentMethod"], "Missing 'paymentMethod' property");

            Assert.AreEqual("vehicle-001", parsed["vehicleId"].ToString());
            Assert.AreEqual("slot-001", parsed["slotId"].ToString());
            Assert.AreEqual("hourly", parsed["packageType"].ToString());

            // Verify no C# PascalCase leaks into JSON
            Assert.IsNull(parsed["VehicleId"], "PascalCase 'VehicleId' should not appear");
            Assert.IsNull(parsed["SlotId"], "PascalCase 'SlotId' should not appear");
        }

        [Test]
        public void should_deserialize_ESP32Response_with_JObject_details()
        {
            // Arrange
            string json = @"{
                ""success"": true,
                ""event"": ""check_in_success"",
                ""barrierAction"": ""open"",
                ""message"": ""Check-in successful"",
                ""gateId"": ""GATE-IN-01"",
                ""bookingId"": ""booking-001"",
                ""plateText"": ""51A-224.56"",
                ""amountDue"": 20000.0,
                ""amountPaid"": null,
                ""processingTimeMs"": 150.5,
                ""details"": {
                    ""carSlot"": {
                        ""code"": ""A-01"",
                        ""zoneId"": ""zone-001""
                    },
                    ""floor"": {
                        ""name"": ""Floor 1"",
                        ""level"": 1
                    }
                }
            }";

            // Act
            var response = JsonConvert.DeserializeObject<ESP32Response>(json);

            // Assert
            Assert.IsTrue(response.Success);
            Assert.AreEqual("check_in_success", response.Event);
            Assert.AreEqual("open", response.BarrierAction);
            Assert.AreEqual("Check-in successful", response.Message);
            Assert.AreEqual("GATE-IN-01", response.GateId);
            Assert.AreEqual("booking-001", response.BookingId);
            Assert.AreEqual("51A-224.56", response.PlateText);
            Assert.AreEqual(20000.0f, response.AmountDue);
            Assert.IsNull(response.AmountPaid);
            Assert.AreEqual(150.5f, response.ProcessingTimeMs, 0.01f);

            // JObject Details — dynamic access
            Assert.IsNotNull(response.Details);
            Assert.AreEqual("A-01", response.Details["carSlot"]?["code"]?.ToString());
            Assert.AreEqual("zone-001", response.Details["carSlot"]?["zoneId"]?.ToString());
            Assert.AreEqual("Floor 1", response.Details["floor"]?["name"]?.ToString());
            Assert.AreEqual(1, response.Details["floor"]?["level"]?.Value<int>());
        }

        [Test]
        public void should_deserialize_SlotData_from_api_json()
        {
            // Arrange
            string json = @"{
                ""id"": ""slot-uuid-001"",
                ""zone"": ""zone-uuid-001"",
                ""code"": ""A-05"",
                ""status"": ""available"",
                ""isAvailable"": true,
                ""camera"": null,
                ""x1"": 400,
                ""y1"": 0,
                ""x2"": 500,
                ""y2"": 200,
                ""createdAt"": ""2026-01-01T00:00:00Z"",
                ""updatedAt"": ""2026-04-01T10:00:00Z""
            }";

            // Act
            var slot = JsonConvert.DeserializeObject<SlotData>(json);

            // Assert
            Assert.AreEqual("slot-uuid-001", slot.Id);
            Assert.AreEqual("zone-uuid-001", slot.Zone);
            Assert.AreEqual("A-05", slot.Code);
            Assert.AreEqual("available", slot.Status);
            Assert.IsTrue(slot.IsAvailable);
            Assert.IsNull(slot.Camera);
            Assert.AreEqual(400, slot.X1);
            Assert.AreEqual(0, slot.Y1);
            Assert.AreEqual(500, slot.X2);
            Assert.AreEqual(200, slot.Y2);
            Assert.IsNotNull(slot.CreatedAt);
            Assert.IsNotNull(slot.UpdatedAt);
        }

        [Test]
        public void should_deserialize_PaginatedResponse_with_nested_results()
        {
            // Arrange
            string json = @"{
                ""count"": 35,
                ""next"": ""http://localhost:8003/parking/slots/?page=2"",
                ""previous"": null,
                ""results"": [
                    {
                        ""id"": ""slot-001"",
                        ""zone"": ""zone-001"",
                        ""code"": ""A-01"",
                        ""status"": ""available"",
                        ""isAvailable"": true,
                        ""camera"": null,
                        ""x1"": 0, ""y1"": 0, ""x2"": 100, ""y2"": 200
                    },
                    {
                        ""id"": ""slot-002"",
                        ""zone"": ""zone-001"",
                        ""code"": ""A-02"",
                        ""status"": ""occupied"",
                        ""isAvailable"": false,
                        ""camera"": null,
                        ""x1"": 100, ""y1"": 0, ""x2"": 200, ""y2"": 200
                    }
                ]
            }";

            // Act
            var paginated = JsonConvert.DeserializeObject<PaginatedResponse<SlotData>>(json);

            // Assert
            Assert.AreEqual(35, paginated.Count);
            Assert.IsNotNull(paginated.Next);
            Assert.IsTrue(paginated.Next.Contains("page=2"));
            Assert.IsNull(paginated.Previous);
            Assert.IsNotNull(paginated.Results);
            Assert.AreEqual(2, paginated.Results.Count);

            Assert.AreEqual("A-01", paginated.Results[0].Code);
            Assert.IsTrue(paginated.Results[0].IsAvailable);
            Assert.AreEqual("A-02", paginated.Results[1].Code);
            Assert.IsFalse(paginated.Results[1].IsAvailable);
        }

        [Test]
        public void should_parse_WsMessage_with_slot_status_update()
        {
            // Arrange — simulate a WebSocket slot_status_update payload
            string json = @"{
                ""slotId"": ""slot-uuid-005"",
                ""zoneId"": ""zone-uuid-001"",
                ""status"": ""occupied"",
                ""vehicleType"": ""Car""
            }";

            // Act
            var update = JsonConvert.DeserializeObject<SlotStatusUpdate>(json);

            // Assert
            Assert.AreEqual("slot-uuid-005", update.SlotId);
            Assert.AreEqual("zone-uuid-001", update.ZoneId);
            Assert.AreEqual("occupied", update.Status);
            Assert.AreEqual("Car", update.VehicleType);
        }

        [Test]
        public void should_serialize_ESP32CheckInRequest_with_null_value_handling()
        {
            // Arrange — only gate_id and qr_data set, others null
            var request = new ESP32CheckInRequest
            {
                GateId = "GATE-IN-01",
                QrData = "{\"booking_id\":\"b1\"}",
                QrCameraUrl = null,
                PlateCameraUrl = null,
                RequestId = null
            };

            // Act
            string json = JsonConvert.SerializeObject(request);
            var parsed = JObject.Parse(json);

            // Assert — NullValueHandling.Ignore means null fields are omitted
            Assert.IsNotNull(parsed["gate_id"]);
            Assert.IsNotNull(parsed["qr_data"]);
            Assert.IsNull(parsed["qr_camera_url"], "Null fields should be omitted");
            Assert.IsNull(parsed["plate_camera_url"], "Null fields should be omitted");
            Assert.IsNull(parsed["request_id"], "Null fields should be omitted");
        }

        [Test]
        public void should_deserialize_BookingData_with_nested_objects()
        {
            // Arrange
            string json = @"{
                ""id"": ""booking-001"",
                ""userId"": ""user-001"",
                ""vehicle"": {
                    ""id"": ""vehicle-001"",
                    ""licensePlate"": ""51A-224.56"",
                    ""vehicleType"": ""Car"",
                    ""name"": ""51A-224.56""
                },
                ""packageType"": ""hourly"",
                ""startTime"": ""2026-04-01T10:00:00Z"",
                ""endTime"": ""2026-04-01T12:00:00Z"",
                ""floor"": {
                    ""id"": ""floor-001"",
                    ""name"": ""Floor 1"",
                    ""level"": 1,
                    ""parkingLotId"": ""lot-001""
                },
                ""zone"": {
                    ""id"": ""zone-001"",
                    ""floorId"": ""floor-001"",
                    ""name"": ""Car Painted F1"",
                    ""vehicleType"": ""Car"",
                    ""capacity"": 10,
                    ""availableSlots"": 5
                },
                ""carSlot"": {
                    ""id"": ""slot-001"",
                    ""zoneId"": ""zone-001"",
                    ""code"": ""A-01"",
                    ""isAvailable"": false
                },
                ""parkingLot"": {
                    ""id"": ""lot-001"",
                    ""name"": ""ParkSmart Central"",
                    ""address"": ""123 Nguyen Hue"",
                    ""latitude"": ""10.762622"",
                    ""longitude"": ""106.660172""
                },
                ""paymentType"": ""on_exit"",
                ""paymentStatus"": ""pending"",
                ""checkInStatus"": ""checked_in"",
                ""price"": ""20000.00"",
                ""checkedInAt"": ""2026-04-01T10:05:00Z"",
                ""qrCodeData"": ""{}"",
                ""createdAt"": ""2026-04-01T09:55:00Z"",
                ""lateFeeApplied"": false
            }";

            // Act
            var booking = JsonConvert.DeserializeObject<BookingData>(json);

            // Assert
            Assert.AreEqual("booking-001", booking.Id);
            Assert.IsNotNull(booking.Vehicle);
            Assert.AreEqual("51A-224.56", booking.Vehicle.LicensePlate);
            Assert.IsNotNull(booking.Floor);
            Assert.AreEqual(1, booking.Floor.Level);
            Assert.IsNotNull(booking.Zone);
            Assert.AreEqual(10, booking.Zone.Capacity);
            Assert.IsNotNull(booking.CarSlot);
            Assert.AreEqual("A-01", booking.CarSlot.Code);
            Assert.IsNotNull(booking.ParkingLot);
            Assert.AreEqual("ParkSmart Central", booking.ParkingLot.Name);
            Assert.AreEqual("checked_in", booking.CheckInStatus);
            Assert.IsFalse(booking.LateFeeApplied);
        }
    }
}
