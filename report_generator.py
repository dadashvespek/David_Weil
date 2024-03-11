import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(json_data):
    doc = SimpleDocTemplate("report.pdf", pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    for key, value in json_data.items():
        elements.append(Paragraph(f"Key: {key}", styles["Heading2"]))
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
    doc.build(elements)

if __name__ == "__main__":
    with open(r"Final_Results\final_0.json") as file:
        json_data = json.load(file)
    generate_pdf(json_data)