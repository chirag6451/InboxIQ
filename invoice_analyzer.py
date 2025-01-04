import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
from config import Config
from utils import rate_limit
import os
from dotenv import load_dotenv
import re
client=OpenAI(
    
    api_key=os.getenv('OPENAI_API_KEY'),
)
# Load environment variables at module level
load_dotenv(override=True)

class InvoiceAnalyzer:
    """Analyzes email content and attachments for invoice information using OpenAI."""

    def __init__(self):
        """Initialize the InvoiceAnalyzer with OpenAI client and logging."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        # Initialize OpenAI client with just the API key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)

        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        self.model = "gpt-4o"

    def analyze_content(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze text content to detect and extract invoice information.
        Falls back to basic keyword detection if OpenAI is not available.
        """
        try:
            self.logger.info("Starting content analysis")
            self.logger.info(f"Analyzing text content (first 100 chars): {text[:100]}...")

            if not self.client:
                self.logger.info("OpenAI not available, using basic detection")
                return self._basic_invoice_analysis(text)

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert invoice analyzer. Your task is to:
1. Determine if the text contains an invoice, bill, receipt, or payment request
2. Extract key invoice details with high precision
3. Assign a confidence score based on the clarity and completeness of information

Analyze the text for:
- Invoice number/reference
- Dates (invoice date, due date)
- Amounts (total, subtotal, tax)
- Currency
- Vendor/Company information
- Payment terms
- Line items if present

Respond with a JSON object in this exact format:
{
    "is_invoice": boolean,
    "confidence": float,  # Scale of 0-1
    "invoice_data": {
        "invoice_number": string | null,
        "date": string | null,
        "due_date": string | null,
        "total_amount": {
            "amount": float | null,
            "currency": string | null
        },
        "subtotal": {
            "amount": float | null,
            "currency": string | null
        },
        "tax_amount": {
            "amount": float | null,
            "currency": string | null
        },
        "vendor": {
            "name": string | null,
            "contact": string | null
        },
        "line_items": array | null,
        "payment_terms": string | null
    }
}"""
                        },
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )

                result = response.choices[0].message.content
                self.logger.info(f"OpenAI analysis completed: {result[:200]}...")

                # Parse the JSON response
                analysis = json.loads(result)

                # Add some basic validation
                if not isinstance(analysis, dict):
                    raise ValueError("Invalid response format from OpenAI")

                self.logger.info(f"Analysis completed with confidence: {analysis.get('confidence', 0)}")
                return analysis

            except Exception as e:
                self.logger.error(f"OpenAI API error: {str(e)}")
                self.logger.info("Falling back to basic detection")
                return self._basic_invoice_analysis(text)

        except Exception as e:
            self.logger.error(f"Error analyzing content: {str(e)}")
            return None

    def _basic_invoice_analysis(self, text: str) -> Dict[str, Any]:
        """
        Perform basic invoice analysis without OpenAI
        Returns a simplified but structured analysis
        """
        text_lower = text.lower()

        # Enhanced keyword sets for different aspects
        amount_patterns = [
            r'(?:[\$₹€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)',  # Currency symbols with amounts
            r'(?:\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:usd|eur|gbp|inr))',  # Amounts with currency codes
            r'total:\s*[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'amount(?:\sdue)?:\s*[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'balance(?:\sdue)?:\s*[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'payment(?:\sof)?:\s*[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'(?:sub)?total:?\s*[\$₹€£]?\s*\d+(?:,\d{3})*(?:\.\d{2})?'
        ]

        date_patterns = [
            r'(?:date|dated):\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}',
            r'(?:due|payment)\s*date:\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}',
            r'(?:invoice|bill)\s*date:\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}',
            r'(?:valid|expiry)\s*(?:until|date):\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}'
        ]

        invoice_identifiers = [
            r'invoice\s*(?:no\.?|number|#|id)?\s*[:.]?\s*[a-z0-9-]+',
            r'bill\s*(?:no\.?|number|#|id)?\s*[:.]?\s*[a-z0-9-]+',
            r'receipt\s*(?:no\.?|number|#|id)?\s*[:.]?\s*[a-z0-9-]+',
            r'order\s*(?:no\.?|number|#|id)?\s*[:.]?\s*[a-z0-9-]+',
            r'transaction\s*(?:no\.?|number|#|id)?\s*[:.]?\s*[a-z0-9-]+'
        ]

        # Calculate confidence based on pattern matches
        amount_matches = sum(1 for pattern in amount_patterns if re.search(pattern, text_lower))
        date_matches = sum(1 for pattern in date_patterns if re.search(pattern, text_lower))
        identifier_matches = sum(1 for pattern in invoice_identifiers if re.search(pattern, text_lower))

        # Weight the matches differently
        confidence = (
            (amount_matches * 0.4) +    # Amount patterns are strong indicators
            (date_matches * 0.3) +      # Dates are good indicators
            (identifier_matches * 0.3)   # Invoice numbers are good indicators
        ) / (
            len(amount_patterns) * 0.4 +
            len(date_patterns) * 0.3 +
            len(invoice_identifiers) * 0.3
        )

        # Extract invoice data
        invoice_data = {}

        # Try to extract invoice number
        for pattern in invoice_identifiers:
            if matches := re.search(pattern, text_lower):
                invoice_num = matches.group(0)
                for prefix in ['invoice', 'bill', 'receipt', 'order', 'transaction', 'no', 'number', '#', 'id', ':', '.']:
                    invoice_num = re.sub(f'{prefix}\s*', '', invoice_num, flags=re.IGNORECASE)
                invoice_data['invoice_number'] = invoice_num.strip()
                break

        # Try to extract amount
        for pattern in amount_patterns:
            if matches := re.search(pattern, text_lower):
                try:
                    amount_str = matches.group(0)
                    amount = float(re.sub(r'[^\d.]', '', amount_str))
                    currency = 'USD'  # Default to USD
                    if '₹' in amount_str or 'inr' in amount_str:
                        currency = 'INR'
                    elif '€' in amount_str or 'eur' in amount_str:
                        currency = 'EUR'
                    elif '£' in amount_str or 'gbp' in amount_str:
                        currency = 'GBP'
                    invoice_data['total_amount'] = {
                        'amount': amount,
                        'currency': currency
                    }
                    break
                except ValueError:
                    continue

        # Try to extract date
        for pattern in date_patterns:
            if matches := re.search(pattern, text_lower):
                date_str = matches.group(0)
                date_str = re.sub(r'.*?:\s*', '', date_str)
                invoice_data['date'] = date_str.strip()
                break

        # Extract vendor information if present
        vendor_patterns = [
            r'(?:from|sender|company|vendor|biller|issued\s*by):\s*([^\n,]+)',
            r'(?:business|merchant)\s*name:\s*([^\n,]+)'
        ]
        for pattern in vendor_patterns:
            if matches := re.search(pattern, text_lower):
                vendor_name = matches.group(1).strip()
                if len(vendor_name) > 3:  # Avoid very short/invalid names
                    invoice_data['vendor'] = {
                        'name': vendor_name.title(),  # Capitalize properly
                        'contact': None
                    }
                    break

        return {
            "is_invoice": confidence > 0.3,  # Lower threshold for basic detection
            "confidence": confidence,
            "invoice_data": invoice_data
        }

    def analyze_pdf_content(self, pdf_text: str) -> Optional[Dict[str, Any]]:
        """Analyze PDF content for invoice information."""
        self.logger.info("Starting PDF content analysis")
        return self.analyze_content(pdf_text)

    def should_forward(self, analysis_result: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if the email should be forwarded based on analysis results.
        Uses different thresholds for OpenAI vs basic detection.
        """
        if not analysis_result:
            self.logger.info("No analysis result available, skipping forward")
            return False

        confidence = analysis_result.get('confidence', 0)
        is_invoice = analysis_result.get('is_invoice', False)

        # Check if we have meaningful invoice data
        invoice_data = analysis_result.get('invoice_data', {})
        has_invoice_data = any([
            invoice_data.get('invoice_number'),
            invoice_data.get('total_amount', {}).get('amount'),
            invoice_data.get('vendor', {}).get('name')
        ])

        # If using OpenAI (indicated by more complex invoice_data structure)
        using_openai = 'tax_amount' in invoice_data or 'payment_terms' in invoice_data
        confidence_threshold = 0.6 if using_openai else 0.3

        should_forward = (
            is_invoice and 
            confidence >= confidence_threshold and
            has_invoice_data
        )

        self.logger.info(
            f"Forward decision: {should_forward} "
            f"(confidence: {confidence:.2f}, "
            f"using_openai: {using_openai})"
        )
        return should_forward