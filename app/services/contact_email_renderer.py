from dataclasses import dataclass
from datetime import timezone
from html import escape
from urllib.parse import quote

from app.domain.models import Contact


@dataclass(frozen=True, slots=True)
class RenderedContactEmail:
    subject: str
    plain_text: str
    html: str


class ContactEmailRenderer:
    """Render accessible plain-text and responsive HTML lead notifications."""

    def render(self, contact: Contact) -> RenderedContactEmail:
        subject_name = " ".join(contact.name.split())
        company = contact.company or "Not provided"
        project_type = contact.project_type or "Not provided"
        budget = contact.budget or "Not provided"
        submitted_at = contact.created_at.astimezone(timezone.utc).strftime(
            "%d %B %Y at %H:%M UTC"
        )
        subject = f"New project enquiry from {subject_name} · CurvatureTech"
        plain_text = "\n".join(
            [
                "CURVATURETECH — NEW PROJECT ENQUIRY",
                "",
                f"Lead ID: #{contact.id}",
                f"Submitted: {submitted_at}",
                f"Name: {contact.name}",
                f"Email: {contact.email}",
                f"Company: {company}",
                f"Project type: {project_type}",
                f"Budget: {budget}",
                "",
                "MESSAGE",
                contact.message,
                "",
                f"Reply directly to this email to contact {contact.name}.",
            ]
        )
        html = self._render_html(
            contact=contact,
            company=company,
            project_type=project_type,
            budget=budget,
            submitted_at=submitted_at,
        )
        return RenderedContactEmail(
            subject=subject,
            plain_text=plain_text,
            html=html,
        )

    @staticmethod
    def _render_html(
        *,
        contact: Contact,
        company: str,
        project_type: str,
        budget: str,
        submitted_at: str,
    ) -> str:
        safe_name = escape(contact.name)
        safe_email = escape(contact.email)
        safe_company = escape(company)
        safe_project_type = escape(project_type)
        safe_budget = escape(budget)
        safe_submitted_at = escape(submitted_at)
        safe_message = escape(contact.message).replace("\n", "<br>")
        reply_href = "mailto:" + quote(contact.email, safe="@.+")

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(f"New enquiry from {contact.name}")}</title>
  <style>
    @media only screen and (max-width: 620px) {{
      .email-shell {{ width: 100% !important; }}
      .email-padding {{ padding-left: 22px !important; padding-right: 22px !important; }}
      .detail-cell {{ display: block !important; width: 100% !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f2f4f8;color:#172033;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
    A new CurvatureTech project enquiry from {safe_name} is ready to review.
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f2f4f8;">
    <tr>
      <td align="center" style="padding:32px 14px;">
        <table role="presentation" width="620" cellspacing="0" cellpadding="0" border="0" class="email-shell" style="width:620px;max-width:620px;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 12px 35px rgba(25,35,61,.12);">
          <tr>
            <td class="email-padding" style="padding:34px 38px;background:#16142f;background-image:linear-gradient(135deg,#17142f,#5b48d6);color:#ffffff;">
              <div style="font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#cfc9ff;">CurvatureTech leads</div>
              <h1 style="margin:12px 0 8px;font-size:28px;line-height:1.25;">A new project enquiry arrived</h1>
              <p style="margin:0;color:#e9e7ff;font-size:15px;line-height:1.6;">{safe_name} would like to start a conversation.</p>
            </td>
          </tr>
          <tr>
            <td class="email-padding" style="padding:30px 38px 12px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #e6e8f0;border-radius:14px;overflow:hidden;">
                <tr>
                  <td class="detail-cell" width="50%" style="padding:18px 20px;border-bottom:1px solid #e6e8f0;vertical-align:top;">
                    <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#7a8194;">Contact</div>
                    <div style="margin-top:7px;font-size:16px;font-weight:700;color:#171b2b;">{safe_name}</div>
                    <a href="{reply_href}" style="display:inline-block;margin-top:4px;color:#5b48d6;text-decoration:none;font-size:14px;">{safe_email}</a>
                  </td>
                  <td class="detail-cell" width="50%" style="padding:18px 20px;border-bottom:1px solid #e6e8f0;vertical-align:top;">
                    <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#7a8194;">Company</div>
                    <div style="margin-top:7px;font-size:15px;line-height:1.5;color:#252a3a;">{safe_company}</div>
                  </td>
                </tr>
                <tr>
                  <td class="detail-cell" width="50%" style="padding:18px 20px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#7a8194;">Project type</div>
                    <div style="margin-top:7px;font-size:15px;line-height:1.5;color:#252a3a;">{safe_project_type}</div>
                  </td>
                  <td class="detail-cell" width="50%" style="padding:18px 20px;vertical-align:top;">
                    <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#7a8194;">Budget</div>
                    <div style="margin-top:7px;font-size:15px;line-height:1.5;color:#252a3a;">{safe_budget}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="email-padding" style="padding:18px 38px 8px;">
              <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#7a8194;">Their message</div>
              <div style="margin-top:10px;padding:20px;background:#f7f6ff;border-left:4px solid #6d5ef7;border-radius:4px 12px 12px 4px;font-size:15px;line-height:1.75;color:#252a3a;">{safe_message}</div>
            </td>
          </tr>
          <tr>
            <td class="email-padding" style="padding:24px 38px 34px;">
              <a href="{reply_href}" style="display:inline-block;padding:13px 22px;background:#5b48d6;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;border-radius:9px;">Reply to {safe_name}</a>
              <div style="margin-top:22px;padding-top:18px;border-top:1px solid #eceef4;color:#7a8194;font-size:12px;line-height:1.6;">
                Lead #{contact.id} · Received {safe_submitted_at}<br>
                Sent securely by the CurvatureTech contact API.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
