import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(json_data, passed_certificates):
    doc = SimpleDocTemplate("report.pdf", pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    for key, value in json_data.items():
        elements.append(Paragraph(f"Certificate No: {key}", styles["Heading2"]))
        elements.append(Spacer(1, 2))

        for item in value:
            if "group" in item:
                group = item["group"]
                nominal = item["nominal"]
                error_message = item["error_message"]
                elements.append(Paragraph(f"{group}", styles["BodyText"]))
                elements.append(Paragraph(f"Nominal Value: {nominal}", styles["BodyText"]))
                elements.append(Paragraph(f"{error_message}", styles["BodyText"]))
                elements.append(Spacer(1, 12))
            elif "Directions not present" in item:
                directions = item["Directions not present"]
                directions_str = ", ".join(directions)
                elements.append(Paragraph(f"Directions not present: {directions_str}", styles["BodyText"]))
                elements.append(Spacer(1, 12))
            elif "STD_Present" in item:
                std_present = item["STD_Present"]
                elements.append(Paragraph(f"No standard deviation present", styles["BodyText"]))
                elements.append(Spacer(1, 12))

        elements.append(Spacer(1, 24))
    if passed_certificates:
        elements.append(Paragraph("List of Certificates That Passed:", styles["Heading1"]))
        elements.append(Spacer(1, 6))
        
        pass_list = ListFlowable([
            ListItem(Paragraph(cert_no, styles["BodyText"])) for cert_no in passed_certificates
        ], bulletType='bullet')
        
        elements.append(pass_list)

    doc.build(elements)
