"""Quick test to verify ReportLab is working"""
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Test PDF", styles['Title'])]
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    print(f"✅ ReportLab is working! Generated {len(pdf)} bytes of PDF")
    print("ReportLab is properly installed and functional.")
except ImportError as e:
    print(f"❌ ReportLab not installed: {e}")
    print("Install with: pip install reportlab")
except Exception as e:
    print(f"❌ ReportLab error: {e}")
    import traceback
    traceback.print_exc()

