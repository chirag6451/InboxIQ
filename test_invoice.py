import os
from invoice_analyzer import InvoiceAnalyzer

def test_invoice_detection():
    # Sample invoice text for testing - Using Apple invoice format
    sample_invoice = """
    Tax Invoice
    APPLE ACCOUNT
    tanvi79@icloud.com
    ORDER ID: MLV2SXN60S
    DOCUMENT NO: 192894861418
    INVOICE DATE: 31 Dec 2024
    SEQUENCE NO: 3-431916660

    BILLED TO:
    Chirag Ahmedabadi
    IndaPoint Technologies Pvt. Ltd., 301 Senate Square
    Opp. Yash complex
    Gotri road
    Baroda, GJ 390021
    IND

    Items:
    Apple Music Family Subscription (Monthly)
    Renews 31 Jan 2025
    SAC:998432
    ₹ 149

    Subtotal: ₹ 126
    IGST charged at 18%: ₹ 23
    Total: ₹ 149
    """

    # Initialize analyzer
    analyzer = InvoiceAnalyzer()

    # Analyze the sample text
    result = analyzer.analyze_content(sample_invoice)

    print("\nAnalysis Results:")
    print(f"Is Invoice: {result.get('is_invoice', False)}")
    print(f"Confidence: {result.get('confidence', 0)}")

    if result and 'invoice_data' in result:
        print("\nInvoice Data:")
        invoice_data = result.get('invoice_data', {})
        print(f"Invoice Number: {invoice_data.get('document_no', '')}")

        total_amount = invoice_data.get('total_amount', {})
        print(f"Total Amount: {total_amount.get('amount')} {total_amount.get('currency')}")
        print(f"Invoice Date: {invoice_data.get('date')}")

        vendor = invoice_data.get('vendor', {})
        print(f"Vendor: {vendor.get('name')}")
    else:
        print("No invoice data detected")

    # Check if it should be forwarded
    should_forward = analyzer.should_forward(result)
    print(f"\nShould Forward: {should_forward}")

if __name__ == "__main__":
    test_invoice_detection()