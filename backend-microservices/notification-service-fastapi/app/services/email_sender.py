"""Gmail SMTP email sender.

Cấu hình qua env vars trong .env:
  EMAIL_HOST_USER=minhht2k4@gmail.com
  EMAIL_HOST_PASSWORD=<16-char Gmail app password — không phải password thường>

Tạo app password tại https://myaccount.google.com/apppasswords sau khi bật 2FA.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


# ─── HTML email templates ────────────────────────────────────────────────

_TYPE_COLOR = {
    "booking":   "#1E40AF",
    "payment":   "#F97316",
    "incident":  "#EF4444",
    "system":    "#10B981",
    "marketing": "#8B5CF6",
}

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f1f5f9;padding:24px 12px;">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <!-- Header band -->
        <tr><td style="background:{color};padding:20px 28px;">
          <table cellpadding="0" cellspacing="0" border="0" width="100%">
            <tr>
              <td><h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;">ParkSmart</h1></td>
              <td align="right"><span style="color:rgba(255,255,255,.85);font-size:12px;text-transform:uppercase;letter-spacing:.5px;">{type_label}</span></td>
            </tr>
          </table>
        </td></tr>

        <!-- Main content -->
        <tr><td style="padding:32px 28px 8px;">
          <h2 style="color:#0f172a;margin:0 0 14px;font-size:20px;font-weight:bold;">{title}</h2>
          <p style="color:#334155;font-size:15px;line-height:1.65;margin:0 0 20px;">{message}</p>
          {extra_html}
        </td></tr>

        <!-- CTA button (optional) -->
        {cta_html}

        <!-- Footer -->
        <tr><td style="background:#f8fafc;padding:18px 28px;border-top:1px solid #e2e8f0;">
          <p style="color:#64748b;font-size:12px;line-height:1.55;margin:0;text-align:center;">
            ParkSmart · Hệ thống quản lý bãi đỗ xe thông minh<br>
            Email tự động — vui lòng không trả lời thư này.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _render_html(notification_type: str, title: str, message: str, data: dict) -> str:
    color = _TYPE_COLOR.get(notification_type, "#1E40AF")
    type_label = {
        "booking": "ĐẶT CHỖ",
        "payment": "THANH TOÁN",
        "incident": "SỰ CỐ",
        "system": "HỆ THỐNG",
        "marketing": "THÔNG BÁO",
    }.get(notification_type, notification_type.upper())

    # Optional extra rows from data (booking_code, amount, etc.)
    extra_rows = []
    for key in ("booking_code", "amount", "slot_code", "vehicle_plate", "lot_name"):
        if key in data and data[key]:
            label = {
                "booking_code":  "Mã booking",
                "amount":        "Số tiền",
                "slot_code":     "Ô đỗ",
                "vehicle_plate": "Biển số",
                "lot_name":      "Bãi đỗ",
            }[key]
            extra_rows.append(
                f'<tr><td style="padding:6px 0;color:#64748b;font-size:13px;">{label}</td>'
                f'<td style="padding:6px 0;color:#0f172a;font-size:14px;font-weight:bold;text-align:right;">{data[key]}</td></tr>'
            )
    extra_html = ""
    if extra_rows:
        extra_html = (
            '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="background:#f8fafc;border-radius:6px;padding:12px 16px;margin:8px 0 4px;">'
            + "".join(extra_rows) +
            '</table>'
        )

    # CTA button if action_url provided
    cta_html = ""
    if data.get("action_url"):
        cta_html = (
            f'<tr><td style="padding:12px 28px 28px;text-align:center;">'
            f'<a href="{data["action_url"]}" style="display:inline-block;padding:12px 28px;background:{color};'
            f'color:#ffffff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:bold;">'
            f'Xem chi tiết</a></td></tr>'
        )

    return _TEMPLATE.format(
        color=color,
        type_label=type_label,
        title=title,
        message=message,
        extra_html=extra_html,
        cta_html=cta_html,
    )


# ─── SMTP send ────────────────────────────────────────────────────────────

def send_notification_email(
    to_email: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> bool:
    """Send notification email via Gmail SMTP. Returns True on success.

    Fails silently (logs warning) if EMAIL_HOST_USER/PASSWORD not configured —
    cho phép service vẫn chạy khi chưa setup credentials.
    """
    if not to_email:
        logger.warning("send_notification_email: no recipient — skip")
        return False

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.warning(
            "EMAIL_HOST_USER / EMAIL_HOST_PASSWORD chưa được set — bỏ qua "
            "gửi email cho %s · subject=%s",
            to_email, title,
        )
        return False

    data = data or {}
    subject = f"[ParkSmart] {title}"
    html_body = _render_html(notification_type, title, message, data)
    # Plain-text fallback
    text_body = f"{title}\n\n{message}\n\n— ParkSmart"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_HOST_USER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=15) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        logger.info(
            "Email sent · to=%s · subject=%s · type=%s",
            to_email, subject, notification_type,
        )
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "Gmail SMTP auth failed — kiểm tra app password 16 ký tự: %s", e
        )
        return False
    except Exception as e:
        logger.exception("Email send failed to %s: %s", to_email, e)
        return False
