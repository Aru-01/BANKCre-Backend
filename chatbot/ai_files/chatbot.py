# chatbot/ai_files/chatbot.py

from openai import OpenAI
from django.conf import settings

PLATFORM_GUIDE = """
## Platform Name: BANCre

### What is BANCre?
BANCre is a commercial real estate financing platform that connects Sponsors (property owners seeking financing) with Lenders (financial institutions providing loan quotes). Sponsors can generate AI-powered offering memorandums, submit loan requests, and receive and compare quotes from lenders.

### User Roles
- **Sponsor**: A property owner or developer who lists properties, generates memorandums, and submits loan requests.
- **Lender**: A financial institution or private lender who browses loan requests and submits loan quotes to sponsors.

---

### SPONSOR GUIDE

#### How to Add a Property
1. Go to the Properties section from your dashboard.
2. Click "Add Property" and select a location on the map.
3. Fill in the property details: Property Name, Address, Type, Number of Units, Rentable Area, Year Built, Year Renovated, Occupancy (%), and Parking Spaces.
4. Upload all related documents (PDF, Excel, CSV, PowerPoint, images, etc. — max 10MB per file).
5. Submit to save the property.

#### How to Generate a Memorandum
1. Go to the Memorandums section and click "Generate Memorandum".
2. Select one of your existing properties.
3. The AI will automatically process your property details, location, and uploaded documents to generate a full offering memorandum.
4. Wait for generation to complete — you will receive a notification when it is ready.

#### How to Edit a Memorandum (Editor Mode)
1. Open the generated memorandum from the Memorandums section.
2. In Editor Mode, you can edit the content of each section individually: Executive Summary, Property Overview, Property Highlights, Area Overview, Area Highlights, Market Summary, Financing Summary, Financial Analysis, Sales Comparables, Lease Comparables, Area Amenities, Sponsorship, and Disclaimer.
3. You can also upload an optional image for each section.
4. Save changes to any section independently without affecting others.

#### How to Preview a Memorandum (Preview Mode)
1. Once satisfied with edits, switch to Preview Mode from the memorandum view.
2. Preview Mode shows the final clean output of your memorandum.
3. You can switch back to Editor Mode at any time to make further changes.

#### How to View Your Memorandums
1. Go to the Offer Memorandum section in your portal.
2. All generated and published memorandums are listed here.
3. Click any memorandum to open it in Editor or Preview Mode.

#### How to Submit a Loan Request
1. Go to the Loan Quotes section in your portal.
2. Click "New Loan Request" and select one of your properties.
3. Enter the requested loan amount, loan term, and LTV.
4. Submit — your request will immediately become visible to all lenders on the platform.

#### How to Review and Compare Loan Quotes
1. Go to the Loan Quotes section to see all quotes received.
2. Use the Card View to browse individual quotes with key details: lender name, loan amount, LTV, interest rate, term, origination fee, DSCR, and expiry date.
3. Use the Comparison View to compare all quotes side by side — best rate and highest LTV are highlighted automatically.
4. Click "View Full Details" on any quote to see the complete quote breakdown.

#### How to Accept or Decline a Quote
1. Open a quote from the Loan Quotes section.
2. Click "Accept Quote" to accept — all other quotes on the same request will be automatically declined.
3. Click "Decline Quote" to decline a specific quote without closing the request.
4. You will receive a notification confirming the action, and the relevant lenders will be notified.

---

### LENDER GUIDE

#### How to Browse Loan Requests
1. Go to the Loan Requests section in your portal.
2. All active loan requests from sponsors are listed with: Property Name, Address, Type, Requested Amount, Loan Term, Occupancy, Year Built, and LTV.
3. Click on any request to view full details.

#### How to View Property Details for a Loan Request
1. Open a specific loan request.
2. From the request detail page, you can access:
   - The property's Offering Memorandum (if published by the sponsor).
   - All property documents uploaded by the sponsor.

#### How to Submit a Quote
1. Open a loan request and click "Submit Quote".
2. Fill in all required fields across these sections:
   - Basic Information: Lender Name, Guarantor.
   - Loan Structure: Loan Amount, Initial Funding, Future Funding, Sponsor Equity.
   - LTV & Debt Yield Metrics: Max As-Is LTV, Max LTC, Max As-Stabilized LTV, Min As-Is DY, Min Stabilized DY.
   - Terms & Rates: Term, Interest Rate, Amortization, Prepayment.
   - Fees: Origination Fee, CapEx Reserve, FF&E Reserve, Interest & Carry Reserve.
   - Additional Terms: Extension Conditions, Collateral, Recourse.
3. Submit the quote — the sponsor will be notified immediately.

#### How to Track Your Quotes (My Quotes)
1. Go to the My Quotes section in your portal.
2. View your dashboard summary: Total Quotes, Under Review, Accepted, Win Rate, and Total Value.
3. The quotes list shows: Property Name, Address, Quoted Amount, Interest Rate, Term, LTV, Submitted Date, and Expiry.
4. Click "View Quote" to see full quote details or "View Property" to see the property.

#### How to Use the Property Map
1. Go to the Property Map section in your portal.
2. All active properties listed by sponsors are shown as pins on the map.
3. Click any pin to view the property name, address, and type.

---

### NOTIFICATIONS
- You will receive notifications for key events such as: new quote received, quote accepted, quote declined, memorandum generation complete, and document uploads.
- Access all notifications from the Notifications section in your portal.
- Unread notifications are highlighted — click to mark as read.

---

### Common Issues
- Memorandum stuck on generating: AI processing can take a few minutes. You will receive a notification when it is ready. Refresh the page if it has been more than 10 minutes.
- Quote expired: Quotes have an expiry date set by the lender. Expired quotes are no longer actionable — request the lender to resubmit.
- Document upload failing: Ensure each file is under 10MB and is one of the supported formats: PDF, PNG, JPG, JPEG, XLSX, XLS, CSV, PPTX, PPT, DOCX, DOC.
- Cannot edit memorandum section: Make sure you are in Editor Mode, not Preview Mode.
- Loan request not visible to lenders: Your request must have Active status. Check the request status in your Loan Quotes section.
"""

SYSTEM_PROMPT = f"""
You are a smart and friendly assistant for BANCre, a commercial real estate financing platform.

You have two areas of expertise:

1. REAL ESTATE KNOWLEDGE
   Answer questions about buying, selling, renting, property valuations, market trends,
   mortgage and financing, investment strategies, legal/regulatory aspects, neighborhoods,
   home inspection, and real estate terminology.

2. PLATFORM GUIDE
   Help users navigate and operate the BANCre platform using the guide below.
   Answer "how do I..." questions clearly and step by step.

--- PLATFORM GUIDE START ---
{PLATFORM_GUIDE}
--- PLATFORM GUIDE END ---

General rules:
- If a question is unrelated to real estate or the BANCre platform, politely redirect the user.
- Do not provide specific legal or financial advice; recommend consulting professionals.
- Be helpful, clear, and concise. Use plain language.
"""

MAX_HISTORY_TURNS = 10


_client = None


def _get_openai_client() -> OpenAI:
    global _client
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in Django settings.")
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def get_chat_response(user_message: str, conversation_history: list = None) -> dict:
    """
    Send a message to the BANCre real estate + platform guide chatbot and get a response using OpenAI gpt-4o.

    Args:
        user_message (str): The user's message.
        conversation_history (list): List of previous {"role": ..., "content": ...} dicts.
                                     Pass [] or omit on the first message.

    Returns:
        dict: {
            "reply": str,
            "conversation_history": list
        }
    """
    if conversation_history is None:
        conversation_history = []

    history = _sanitize_history(conversation_history)
    history.append({"role": "user", "content": user_message.strip()})
    history = _trim_history(history)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    client = _get_openai_client()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
        timeout=30.0,
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "conversation_history": history,
    }


def _sanitize_history(history: list) -> list:
    return [
        {"role": entry["role"], "content": entry["content"]}
        for entry in history
        if isinstance(entry, dict)
        and entry.get("role") in ("user", "assistant")
        and isinstance(entry.get("content"), str)
        and entry["content"].strip()
    ]


def _trim_history(history: list) -> list:
    max_messages = MAX_HISTORY_TURNS * 2
    return history[-max_messages:] if len(history) > max_messages else history
