using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace ParkingSim.API
{
    // ══════════════════════════════════════════════
    //          PARKING SERVICE MODELS (:8003)
    // ══════════════════════════════════════════════

    [Serializable]
    public class LotData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("address")] public string Address;
        [JsonProperty("latitude")] public string Latitude;
        [JsonProperty("longitude")] public string Longitude;
        [JsonProperty("totalSlots")] public int TotalSlots;
        [JsonProperty("availableSlots")] public int AvailableSlots;
        [JsonProperty("pricePerHour")] public string PricePerHour;
        [JsonProperty("isOpen")] public bool IsOpen;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("updatedAt")] public string UpdatedAt;
    }

    [Serializable]
    public class FloorData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("parkingLot")] public string ParkingLot;
        [JsonProperty("level")] public int Level;
        [JsonProperty("name")] public string Name;
        // zones[] populated in both GET /parking/floors/{id}/ and GET /parking/floors/?lot_id={id}
        [JsonProperty("zones")] public List<ZoneData> Zones;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("updatedAt")] public string UpdatedAt;
    }

    [Serializable]
    public class ZoneData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("floor")] public string Floor;
        [JsonProperty("floorLevel")] public int FloorLevel;
        [JsonProperty("name")] public string Name;
        [JsonProperty("vehicleType")] public string VehicleType;
        [JsonProperty("capacity")] public int Capacity;
        [JsonProperty("availableSlots")] public int AvailableSlots;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("updatedAt")] public string UpdatedAt;
    }

    [Serializable]
    public class SlotData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("zone")] public string Zone;
        [JsonProperty("code")] public string Code;
        [JsonProperty("status")] public string Status;
        [JsonProperty("isAvailable")] public bool IsAvailable;
        [JsonProperty("camera")] public string Camera;
        [JsonProperty("x1")] public int X1;
        [JsonProperty("y1")] public int Y1;
        [JsonProperty("x2")] public int X2;
        [JsonProperty("y2")] public int Y2;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("updatedAt")] public string UpdatedAt;
    }

    // ══════════════════════════════════════════════
    //          VEHICLE SERVICE MODELS (:8004)
    // ══════════════════════════════════════════════

    [Serializable]
    public class VehicleData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("userId")] public string UserId;
        [JsonProperty("licensePlate")] public string LicensePlate;
        [JsonProperty("vehicleType")] public string VehicleType;
        [JsonProperty("brand")] public string Brand;
        [JsonProperty("model")] public string Model;
        [JsonProperty("color")] public string Color;
        [JsonProperty("isDefault")] public bool IsDefault;
        [JsonProperty("name")] public string Name;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("updatedAt")] public string UpdatedAt;
    }

    // ══════════════════════════════════════════════
    //         BOOKING SERVICE MODELS (:8002)
    // ══════════════════════════════════════════════

    [Serializable]
    public class BookingCreateRequest
    {
        [JsonProperty("vehicleId")] public string VehicleId;
        [JsonProperty("slotId")] public string SlotId;
        [JsonProperty("zoneId")] public string ZoneId;
        [JsonProperty("parkingLotId")] public string ParkingLotId;
        [JsonProperty("startTime")] public string StartTime;
        [JsonProperty("endTime")] public string EndTime;
        [JsonProperty("packageType")] public string PackageType;
        [JsonProperty("paymentMethod")] public string PaymentMethod;
    }

    [Serializable]
    public class BookingCreateResponse
    {
        [JsonProperty("booking")] public BookingData Booking;
        [JsonProperty("message")] public string Message;
        [JsonProperty("qrCode")] public string QrCode;
    }

    [Serializable]
    public class BookingData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("userId")] public string UserId;
        [JsonProperty("vehicle")] public BookingVehicleInfo Vehicle;
        [JsonProperty("packageType")] public string PackageType;
        [JsonProperty("startTime")] public string StartTime;
        [JsonProperty("endTime")] public string EndTime;
        [JsonProperty("floor")] public BookingFloorInfo Floor;
        [JsonProperty("zone")] public BookingZoneInfo Zone;
        [JsonProperty("carSlot")] public BookingSlotInfo CarSlot;
        [JsonProperty("parkingLot")] public BookingLotInfo ParkingLot;
        [JsonProperty("paymentType")] public string PaymentType;
        [JsonProperty("paymentStatus")] public string PaymentStatus;
        [JsonProperty("checkInStatus")] public string CheckInStatus;
        [JsonProperty("price")] public string Price;
        [JsonProperty("checkedInAt")] public string CheckedInAt;
        [JsonProperty("checkedOutAt")] public string CheckedOutAt;
        [JsonProperty("qrCodeData")] public string QrCodeData;
        [JsonProperty("createdAt")] public string CreatedAt;
        [JsonProperty("hourlyStart")] public string HourlyStart;
        [JsonProperty("hourlyEnd")] public string HourlyEnd;
        [JsonProperty("extendedUntil")] public string ExtendedUntil;
        [JsonProperty("lateFeeApplied")] public bool LateFeeApplied;
    }

    [Serializable]
    public class BookingVehicleInfo
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("licensePlate")] public string LicensePlate;
        [JsonProperty("vehicleType")] public string VehicleType;
        [JsonProperty("name")] public string Name;
    }

    [Serializable]
    public class BookingFloorInfo
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("level")] public int Level;
        [JsonProperty("parkingLotId")] public string ParkingLotId;
    }

    [Serializable]
    public class BookingZoneInfo
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("floorId")] public string FloorId;
        [JsonProperty("name")] public string Name;
        [JsonProperty("vehicleType")] public string VehicleType;
        [JsonProperty("capacity")] public int Capacity;
        [JsonProperty("availableSlots")] public int AvailableSlots;
    }

    [Serializable]
    public class BookingSlotInfo
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("zoneId")] public string ZoneId;
        [JsonProperty("code")] public string Code;
        [JsonProperty("isAvailable")] public bool IsAvailable;
    }

    [Serializable]
    public class BookingLotInfo
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("name")] public string Name;
        [JsonProperty("address")] public string Address;
        [JsonProperty("latitude")] public string Latitude;
        [JsonProperty("longitude")] public string Longitude;
    }

    // ══════════════════════════════════════════════
    //       AI / ESP32 SERVICE MODELS (:8009)
    // ══════════════════════════════════════════════

    [Serializable]
    public class ESP32CheckInRequest
    {
        [JsonProperty("gate_id")] public string GateId;

        [JsonProperty("qr_data", NullValueHandling = NullValueHandling.Ignore)]
        public string QrData;

        [JsonProperty("qr_camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string QrCameraUrl;

        [JsonProperty("plate_camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string PlateCameraUrl;

        [JsonProperty("request_id", NullValueHandling = NullValueHandling.Ignore)]
        public string RequestId;
    }

    [Serializable]
    public class ESP32CheckOutRequest
    {
        [JsonProperty("gate_id")] public string GateId;

        [JsonProperty("qr_data", NullValueHandling = NullValueHandling.Ignore)]
        public string QrData;

        [JsonProperty("qr_camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string QrCameraUrl;

        [JsonProperty("plate_camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string PlateCameraUrl;

        [JsonProperty("request_id", NullValueHandling = NullValueHandling.Ignore)]
        public string RequestId;
    }

    [Serializable]
    public class ESP32VerifySlotRequest
    {
        [JsonProperty("slot_code")] public string SlotCode;
        [JsonProperty("zone_id")] public string ZoneId;
        [JsonProperty("gate_id")] public string GateId;

        [JsonProperty("qr_data", NullValueHandling = NullValueHandling.Ignore)]
        public string QrData;

        [JsonProperty("qr_camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string QrCameraUrl;

        [JsonProperty("request_id", NullValueHandling = NullValueHandling.Ignore)]
        public string RequestId;
    }

    [Serializable]
    public class ESP32CashPaymentRequest
    {
        [JsonProperty("booking_id")] public string BookingId;

        [JsonProperty("image_base64", NullValueHandling = NullValueHandling.Ignore)]
        public string ImageBase64;

        [JsonProperty("camera_url", NullValueHandling = NullValueHandling.Ignore)]
        public string CameraUrl;

        [JsonProperty("gate_id")] public string GateId;

        [JsonProperty("request_id", NullValueHandling = NullValueHandling.Ignore)]
        public string RequestId;
    }

    [Serializable]
    public class ESP32Response
    {
        [JsonProperty("success")] public bool Success;
        [JsonProperty("event")] public string Event;
        [JsonProperty("barrierAction")] public string BarrierAction;
        [JsonProperty("message")] public string Message;
        [JsonProperty("gateId")] public string GateId;
        [JsonProperty("bookingId")] public string BookingId;
        [JsonProperty("plateText")] public string PlateText;
        [JsonProperty("plateImageUrl")] public string PlateImageUrl;
        [JsonProperty("amountDue")] public float? AmountDue;
        [JsonProperty("amountPaid")] public float? AmountPaid;
        [JsonProperty("processingTimeMs")] public float ProcessingTimeMs;

        // JObject for dynamic access: Details?["carSlot"]?["code"]?.ToString()
        [JsonProperty("details")] public JObject Details;
    }

    [Serializable]
    public class ESP32AckResponse
    {
        [JsonProperty("success")] public bool Success;
        [JsonProperty("message")] public string Message;
    }

    [Serializable]
    public class ESP32DeviceRegisterRequest
    {
        [JsonProperty("device_id")] public string DeviceId;
        [JsonProperty("ip")] public string Ip;
        [JsonProperty("firmware")] public string Firmware;
        [JsonProperty("gpio_config")] public Dictionary<string, int> GpioConfig;
    }

    [Serializable]
    public class ESP32HeartbeatRequest
    {
        [JsonProperty("device_id")] public string DeviceId;
        [JsonProperty("status")] public string Status;
        [JsonProperty("wifi_rssi")] public int WifiRssi;
    }

    [Serializable]
    public class ESP32LogRequest
    {
        [JsonProperty("device_id")] public string DeviceId;
        [JsonProperty("level")] public string Level;
        [JsonProperty("message")] public string Message;
    }

    [Serializable]
    public class PlateScanResult
    {
        [JsonProperty("plateText")] public string PlateText;
        [JsonProperty("decision")] public string Decision;
        [JsonProperty("confidence")] public float Confidence;
        [JsonProperty("detectionConfidence")] public float DetectionConfidence;
        [JsonProperty("isBlurry")] public bool IsBlurry;
        [JsonProperty("blurScore")] public float BlurScore;
        [JsonProperty("ocrMethod")] public string OcrMethod;
        [JsonProperty("rawCandidates")] public List<string> RawCandidates;
        [JsonProperty("warning")] public string Warning;
        [JsonProperty("message")] public string Message;
        [JsonProperty("processingTimeMs")] public float ProcessingTimeMs;
    }

    [Serializable]
    public class QrScanResult
    {
        [JsonProperty("found")] public bool Found;
        [JsonProperty("qr_data")] public string QrData;
        [JsonProperty("booking_id")] public string BookingId;
        [JsonProperty("error")] public string Error;
    }

    // ══════════════════════════════════════════════
    //          WEBSOCKET MODELS (:8006)
    // ══════════════════════════════════════════════

    [Serializable]
    public class WsSubscribeMessage
    {
        [JsonProperty("type")] public string Type;
        [JsonProperty("data")] public WsSubscribeData Data;
    }

    [Serializable]
    public class WsSubscribeData
    {
        [JsonProperty("channel")] public string Channel;
    }

    [Serializable]
    public class SlotStatusUpdate
    {
        [JsonProperty("slotId")] public string SlotId;
        [JsonProperty("zoneId")] public string ZoneId;
        [JsonProperty("status")] public string Status;
        [JsonProperty("vehicleType")] public string VehicleType;
    }

    [Serializable]
    public class CheckinSuccessData
    {
        [JsonProperty("booking_id")] public string BookingId;
        [JsonProperty("plate")]       public string Plate;
        [JsonProperty("slot_code")]   public string SlotCode;
        [JsonProperty("vehicle_type")]public string VehicleType;
        [JsonProperty("qr_data")]     public string QrData;
    }

    // ══════════════════════════════════════════════
    //          ERROR RESPONSE MODELS
    // ══════════════════════════════════════════════

    [Serializable]
    public class DjangoErrorResponse
    {
        [JsonProperty("error")] public string Error;
        [JsonProperty("detail")] public string Detail;
    }

    [Serializable]
    public class GatewayErrorResponse
    {
        [JsonProperty("error")] public string Error;
        [JsonProperty("service")] public string Service;
        [JsonProperty("path")] public string Path;
    }

    // ══════════════════════════════════════════════
    //          PAGINATION WRAPPER
    // ══════════════════════════════════════════════

    [Serializable]
    public class PaginatedResponse<T>
    {
        [JsonProperty("count")] public int Count;
        [JsonProperty("next")] public string Next;
        [JsonProperty("previous")] public string Previous;
        [JsonProperty("results")] public List<T> Results;
    }

    // ══════════════════════════════════════════════
    //     SHARED BOOKING STATE DTO (for ESP32)
    // ══════════════════════════════════════════════

    [Serializable]
    public class ActiveBooking
    {
        public string BookingId;
        public string QrCodeData;
        public string LicensePlate;
        public string SlotCode;
        public string ZoneId;
        public string VehicleType;
        public string CheckInStatus;
    }

    // ══════════════════════════════════════════════
    //          AUTH RESPONSE MODELS
    // ══════════════════════════════════════════════

    [Serializable]
    public class LoginResponse
    {
        [JsonProperty("user")] public LoginUserData User;
        [JsonProperty("message")] public string Message;
    }

    [Serializable]
    public class LoginUserData
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("email")] public string Email;
        [JsonProperty("username")] public string Username;
        [JsonProperty("role")] public string Role;
        [JsonProperty("avatar")] public string Avatar;
    }

    // ══════════════════════════════════════════════
    //          API RESPONSE WRAPPER
    // ══════════════════════════════════════════════

    [Serializable]
    public class ApiResponse<T>
    {
        public bool IsSuccess;
        public T Data;
        public string ErrorMessage;
        public string ErrorCode;
        public int StatusCode;
    }

    [Serializable]
    public class ApiErrorResponse
    {
        [JsonProperty("success")] public bool Success;
        [JsonProperty("error")] public ApiErrorDetail Error;
    }

    [Serializable]
    public class ApiErrorDetail
    {
        [JsonProperty("code")] public string Code;
        [JsonProperty("message")] public string Message;
    }
}
