using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ParkingSim.API
{
    public class SharedBookingState : MonoBehaviour
    {
        public static SharedBookingState Instance { get; private set; }

        public event Action<ActiveBooking> OnBookingAdded;
        public event Action<string> OnBookingRemoved;

        [SerializeField] private List<ActiveBooking> activeBookings = new List<ActiveBooking>();

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            if (transform.parent == null)
                DontDestroyOnLoad(gameObject);
        }

        public void AddBooking(BookingCreateResponse response)
        {
            if (response?.Booking == null) return;

            var existing = activeBookings.Find(b => b.BookingId == response.Booking.Id);
            if (existing != null) return;

            var booking = new ActiveBooking
            {
                BookingId = response.Booking.Id,
                QrCodeData = response.QrCode,
                LicensePlate = response.Booking.Vehicle?.LicensePlate,
                SlotCode = response.Booking.CarSlot?.Code,
                ZoneId = response.Booking.Zone?.Id,
                VehicleType = response.Booking.Vehicle?.VehicleType,
                CheckInStatus = "not_checked_in"
            };

            activeBookings.Add(booking);
            OnBookingAdded?.Invoke(booking);
        }

        public void RemoveBooking(string bookingId)
        {
            int removed = activeBookings.RemoveAll(b => b.BookingId == bookingId);
            if (removed > 0)
            {
                OnBookingRemoved?.Invoke(bookingId);
            }
        }

        private static string NormalizeId(string id) =>
            string.IsNullOrEmpty(id) ? string.Empty : id.Replace("-", "").ToLowerInvariant();

        private ActiveBooking FindBooking(string bookingId)
        {
            if (string.IsNullOrEmpty(bookingId)) return null;
            string needle = NormalizeId(bookingId);
            return activeBookings.Find(b => NormalizeId(b.BookingId) == needle);
        }

        public void UpdateStatus(string bookingId, string newStatus)
        {
            var booking = FindBooking(bookingId);
            if (booking != null)
            {
                booking.CheckInStatus = newStatus;
            }
        }

        public void UpdateSlotCode(string bookingId, string slotCode)
        {
            var booking = FindBooking(bookingId);
            if (booking != null && !string.IsNullOrEmpty(slotCode) && slotCode != "unknown")
            {
                booking.SlotCode = slotCode;
            }
        }

        public ActiveBooking GetBookingById(string bookingId) => FindBooking(bookingId);

        public ActiveBooking GetBookingByPlate(string plate)
        {
            return activeBookings.Find(b =>
                string.Equals(b.LicensePlate, plate, StringComparison.OrdinalIgnoreCase));
        }

        public ActiveBooking GetBookingByQr(string qrData)
        {
            return activeBookings.Find(b =>
                string.Equals(b.QrCodeData, qrData, StringComparison.OrdinalIgnoreCase));
        }

        public ActiveBooking GetBookingBySlotCode(string slotCode)
        {
            return activeBookings.Find(b =>
                string.Equals(b.SlotCode, slotCode, StringComparison.OrdinalIgnoreCase));
        }

        public List<ActiveBooking> GetActiveBookings()
        {
            return new List<ActiveBooking>(activeBookings);
        }

        public List<ActiveBooking> GetNotCheckedIn()
        {
            return activeBookings.Where(b => b.CheckInStatus == "not_checked_in").ToList();
        }

        /// <summary>
        /// Return only bookings eligible for check-in (status = not_checked_in).
        /// Excludes bookings already checked_in, checked_out, no_show, or cancelled.
        /// </summary>
        public List<(string label, ActiveBooking booking)> GetActiveBookingsForDropdown()
        {
            return activeBookings
                .Where(b => b.CheckInStatus == "not_checked_in")
                .Select(b =>
                {
                    string shortId = b.BookingId != null && b.BookingId.Length >= 8
                        ? b.BookingId.Substring(0, 8)
                        : b.BookingId ?? "???";
                    string label = $"{b.LicensePlate} → {b.SlotCode} ({shortId})";
                    return (label, b);
                })
                .ToList();
        }

        /// <summary>
        /// Trả TẤT CẢ booking còn hoạt động (not_checked_in + checked_in) với status
        /// prefix trong label — single dropdown UX. Dùng làm list hiển thị chung ở
        /// ESP32Simulator cho cả Check-In / Verify / Check-Out.
        /// </summary>
        public List<(string label, ActiveBooking booking)> GetAllActiveForDropdown()
        {
            return activeBookings
                .Where(b => b.CheckInStatus == "not_checked_in" || b.CheckInStatus == "checked_in")
                .Select(b =>
                {
                    string shortId = b.BookingId != null && b.BookingId.Length >= 8
                        ? b.BookingId.Substring(0, 8)
                        : b.BookingId ?? "???";
                    string icon = b.CheckInStatus == "checked_in" ? "✓" : "⏳";
                    string label = $"{icon} {b.LicensePlate} → {b.SlotCode} ({shortId})";
                    return (label, b);
                })
                .ToList();
        }

        /// <summary>
        /// Return bookings already checked-in (eligible for check-out).
        /// </summary>
        public List<(string label, ActiveBooking booking)> GetCheckedInBookingsForDropdown()
        {
            return activeBookings
                .Where(b => b.CheckInStatus == "checked_in")
                .Select(b =>
                {
                    string shortId = b.BookingId != null && b.BookingId.Length >= 8
                        ? b.BookingId.Substring(0, 8)
                        : b.BookingId ?? "???";
                    string label = $"{b.LicensePlate} → {b.SlotCode} ({shortId})";
                    return (label, b);
                })
                .ToList();
        }

        /// <summary>
        /// Sync active bookings fetched from the API (e.g. created on the web).
        /// Skips bookings already stored locally. Only imports not-yet-checked-in bookings.
        /// </summary>
        public int SyncFromApi(List<BookingData> apiBookings)
        {
            int added = 0;
            foreach (var b in apiBookings)
            {
                if (b == null || string.IsNullOrEmpty(b.Id)) continue;
                if (b.CheckInStatus == "checked_out") continue;

                // Normalized comparison tránh tạo duplicate khi backend trả id có dash
                // trong khi local script seed ra no-dash (hoặc ngược lại).
                var existing = FindBooking(b.Id);
                if (existing != null)
                {
                    // Đã tồn tại: KHÔNG overwrite CheckInStatus local vì DoCheckIn
                    // vừa update nó thành "checked_in" — backend sync có thể còn
                    // trả "not_checked_in" nếu eventual consistency chưa kịp.
                    // Chỉ cập nhật slot/qr nếu trước đó thiếu.
                    if (string.IsNullOrEmpty(existing.SlotCode) && !string.IsNullOrEmpty(b.CarSlot?.Code))
                        existing.SlotCode = b.CarSlot.Code;
                    if (string.IsNullOrEmpty(existing.QrCodeData) && !string.IsNullOrEmpty(b.QrCodeData))
                        existing.QrCodeData = b.QrCodeData;
                    continue;
                }

                if (b.CheckInStatus == "checked_in") continue; // don't auto-import already checked-in

                var active = new ActiveBooking
                {
                    BookingId = b.Id,
                    QrCodeData = b.QrCodeData,
                    LicensePlate = b.Vehicle?.LicensePlate,
                    SlotCode = b.CarSlot?.Code,
                    ZoneId = b.Zone?.Id,
                    VehicleType = b.Vehicle?.VehicleType,
                    CheckInStatus = b.CheckInStatus ?? "not_checked_in"
                };
                activeBookings.Add(active);
                OnBookingAdded?.Invoke(active);
                added++;
            }
            return added;
        }

        public void Clear()
        {
            activeBookings.Clear();
        }
    }
}
