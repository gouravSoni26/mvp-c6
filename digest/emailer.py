from flask import render_template

import resend

import config
from digest.builder import generate_subject_line


def send_digest_email(digest_data, context):
    """Render and send the digest email via Resend."""
    resend.api_key = config.RESEND_API_KEY

    fmt = context.get("digest_format", "top_3")
    template_map = {
        "top_3": "email/top3.html",
        "grouped_by_source": "email/grouped.html",
        "themed_by_topic": "email/themed.html",
    }
    template = template_map.get(fmt, "email/top3.html")

    # Render email HTML
    # Note: This must be called within Flask app context
    from app import app
    with app.app_context():
        html = render_template(
            template,
            digest=digest_data,
            ctx=context,
            base_url=config.APP_BASE_URL,
        )

    subject = generate_subject_line(
        digest_data.get("must_reads", []),
        digest_data.get("total", 0),
    )

    params = {
        "from": config.DIGEST_FROM_EMAIL,
        "to": [config.DIGEST_TO_EMAIL],
        "subject": subject,
        "html": html,
    }

    response = resend.Emails.send(params)
    print(f"  Email sent! ID: {response.get('id', 'unknown')}")
    return response
