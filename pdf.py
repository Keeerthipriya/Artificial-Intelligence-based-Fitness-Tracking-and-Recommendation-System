from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib.utils import simpleSplit
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime

class FitTrackerPDF:
    def __init__(self, document_type="fitness"):
        """Initializes a PDF generator with improved margins and layout."""
        self.buffer = BytesIO()
        self.doc = canvas.Canvas(self.buffer, pagesize=letter)
        self.width, self.height = letter
        self.document_type = document_type
        
        # Enhanced color palette
        self.brand_color = HexColor('#4F46E5')  # Indigo-600
        self.accent_color = HexColor('#7C3AED')   # Purple-600
        self.success_color = HexColor('#059669')  # Green-600
        self.warning_color = HexColor('#D97706')  # Amber-600
        self.info_color = HexColor('#2563EB')     # Blue-600
        self.text_color = HexColor('#1F2937')     # Gray-800
        self.light_gray = HexColor('#F3F4F6')     # Gray-100
        
        # Improved margins for better content containment
        self.left_margin = 1.0 * inch
        self.right_margin = 1.0 * inch
        self.top_margin = 1.0 * inch
        self.bottom_margin = 1.0 * inch
        self.content_width = self.width - (self.left_margin + self.right_margin)
    
    def add_page_header(self):
        """Draws a modern, compact header at the top of the page."""
        header_height = 1.5 * inch
        
        # Header background
        self.doc.setFillColor(self.brand_color)
        self.doc.rect(0, self.height - header_height, self.width, header_height, fill=True)
        
        # Decorative circles for a modern flair
        self.doc.setFillColor(self.accent_color)
        for i in range(3):
            x = self.width - (0.8 + i*0.4) * inch
            y = self.height - (0.6 + i*0.3) * inch
            size = (0.3 - i*0.08) * inch
            self.doc.circle(x, y, size, fill=True)
        
        # Title text
        self.doc.setFillColor(HexColor('#FFFFFF'))
        self.doc.setFont("Helvetica-Bold", 24)
        title_text = "FitTracker"
        self.doc.drawString(self.left_margin, self.height - 0.8*inch, title_text)
        
        # Subtitle based on document type
        self.doc.setFont("Helvetica", 14)
        subtitle = "Professional Fitness Plan" if self.document_type == "fitness" else "Custom Meal Plan"
        self.doc.drawString(self.left_margin, self.height - 1.2*inch, subtitle)
        
        return self.height - header_height - 0.5*inch

    def add_section_title(self, title, y_position, icon=None):
        """Enhanced section title with better boundary handling."""
        header_height = 1 * inch
        
        # Adjusted width to prevent overflow
        self.doc.setFillColor(self.brand_color)
        self.doc.roundRect(
            self.left_margin,
            y_position - 0.8*inch,
            self.content_width,
            header_height,
            10,
            fill=True
        )
        
        # Icon + Title with adjusted positioning
        self.doc.setFillColor(HexColor('#FFFFFF'))
        self.doc.setFont("Helvetica-Bold", 22)
        icon_map = {
            "workout": "💪", "nutrition": "🥗", "schedule": "📅",
            "exercises": "🏋️", "progress": "📈", "meal": "🍽️",
            "profile": "👤"
        }
        icon = icon_map.get(icon.lower(), "📌") if icon else "📌"
        text = f"{icon}  {title}"
        
        # Truncate title if text exceeds available width
        while self.doc.stringWidth(text, "Helvetica-Bold", 22) > (self.content_width - 0.4*inch):
            title = title[:-1]
            text = f"{icon}  {title}..."
        
        self.doc.drawString(self.left_margin + 0.2*inch, y_position - 0.4*inch, text)
        return y_position - header_height

    def add_content_card(self, title, content, y_position):
        """Enhanced content card with improved text wrapping."""
        card_padding = 0.4 * inch
        lines = content.split('\n')
        lines = [line.replace('*', '•') for line in lines]
        
        # Calculate available width for text
        available_width = self.content_width - 0.8*inch
        text_lines = []
        for line in lines:
            if self.doc.stringWidth(line, "Helvetica", 14) > available_width:
                wrapped = simpleSplit(line, "Helvetica", 14, available_width)
                text_lines.extend(wrapped)
            else:
                text_lines.append(line)
        
        line_spacing = 0.3 * inch
        estimated_height = (len(text_lines) * line_spacing) + (0.6 * inch)
        
        # Card background
        self.doc.setFillColor(HexColor('#F8FAFC'))
        self.doc.roundRect(
            self.left_margin,
            y_position - estimated_height - card_padding,
            self.content_width,
            estimated_height + card_padding,
            8,
            fill=True
        )
        
        # Accent bar for visual flair
        self.doc.setFillColor(self.accent_color)
        self.doc.roundRect(
            self.left_margin,
            y_position - estimated_height - card_padding,
            0.25*inch,
            estimated_height + card_padding,
            4,
            fill=True
        )
        
        # Render title
        text_x = self.left_margin + 0.4*inch
        text_y = y_position - 0.4*inch
        self.doc.setFillColor(self.text_color)
        self.doc.setFont("Helvetica-Bold", 18)
        self.doc.drawString(text_x, text_y, title)
        text_y -= 0.4*inch
        self.doc.setFont("Helvetica", 14)
        
        # Render content with improved formatting
        for line in text_lines:
            if text_y < self.bottom_margin:
                self.doc.showPage()
                text_y = self.add_page_header() - 1.5*inch
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                self.doc.setFont("Helvetica-Bold", 14)
                self.doc.setFillColor(HexColor('#1E40AF'))
                self.doc.drawString(text_x, text_y, parts[0] + ':')
                if len(parts) > 1:
                    self.doc.setFont("Helvetica", 14)
                    self.doc.setFillColor(self.text_color)
                    offset = self.doc.stringWidth(parts[0] + ':  ', "Helvetica-Bold", 14)
                    self.doc.drawString(text_x + offset, text_y, parts[1])
            else:
                self.doc.setFont("Helvetica", 14)
                self.doc.setFillColor(HexColor('#374151'))
                if line.startswith('•'):
                    self.doc.setFillColor(self.accent_color)
                    self.doc.circle(text_x - 0.15*inch, text_y + 4, 3, fill=True)
                    self.doc.setFillColor(HexColor('#374151'))
                    self.doc.drawString(text_x + 0.1*inch, text_y, line[1:].strip())
                else:
                    self.doc.drawString(text_x, text_y, line)
            text_y -= line_spacing
        
        return text_y - 0.4*inch

    def add_info_card(self, title, content, y_position):
        """Enhanced info card with content wrapping."""
        card_height = 1.0 * inch
        available_width = self.content_width - 0.8*inch
        
        # Wrap content if too long
        if self.doc.stringWidth(content, "Helvetica", 14) > available_width:
            content_lines = simpleSplit(content, "Helvetica", 14, available_width)
            content = content_lines[0]
            if len(content_lines) > 1:
                content += "..."
        
        # Draw background
        self.doc.setFillColor(HexColor('#F8FAFC'))
        self.doc.roundRect(
            self.left_margin,
            y_position - card_height,
            self.content_width,
            card_height,
            10,
            fill=True
        )
        
        # Accent bar
        self.doc.setFillColor(self.accent_color)
        self.doc.roundRect(
            self.left_margin,
            y_position - card_height,
            0.25*inch,
            card_height,
            5,
            fill=True
        )
        
        # Title text
        self.doc.setFillColor(HexColor('#1E40AF'))
        self.doc.setFont("Helvetica-Bold", 16)
        self.doc.drawString(self.left_margin + 0.4*inch, y_position - 0.5*inch, title)
        
        # Content text
        self.doc.setFont("Helvetica", 14)
        self.doc.setFillColor(HexColor('#374151'))
        self.doc.drawString(self.left_margin + 0.4*inch, y_position - 0.9*inch, content)
        
        return y_position - (card_height + 0.4*inch)

    def add_footer(self):
        """Enhanced footer with proper text positioning."""
        footer_height = 0.8 * inch
        self.doc.setFillColor(self.light_gray)
        self.doc.rect(0, 0, self.width, footer_height, fill=True)
        self.doc.setStrokeColor(HexColor('#E5E7EB'))
        self.doc.setLineWidth(0.5)
        self.doc.line(0, footer_height, self.width, footer_height)
        self.doc.setFillColor(HexColor('#6B7280'))
        self.doc.setFont("Helvetica", 9)
        self.doc.drawString(self.left_margin, 0.5*inch, "FitTracker - Your Personal Fitness Assistant")
        center_text = "www.fittracker.com"
        center_width = self.doc.stringWidth(center_text, "Helvetica", 9)
        self.doc.drawString((self.width - center_width) / 2, 0.5*inch, center_text)
        date_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        date_width = self.doc.stringWidth(date_text, "Helvetica", 9)
        self.doc.drawString(self.width - self.right_margin - date_width, 0.5*inch, date_text)

def create_fitness_plan_pdf(user_data, plan):
    """Generates a Fitness Plan PDF using FitTrackerPDF.
       The workout plan section is placed on the second page.
    """
    pdf = FitTrackerPDF("fitness")
    y_position = pdf.height - pdf.top_margin

    # First page: Header and Profile Section
    y_position = pdf.add_page_header()
    y_position = pdf.add_section_title("Your Fitness Profile", y_position, "profile")
    
    profile_items = [
        ("Goal", f"🎯 {user_data.get('goal', 'Not specified')}"),
        ("Current Stats", f"📊 {user_data.get('weight', 'N/A')} kg | {user_data.get('height', 'N/A')} cm"),
        ("Daily Energy", f"🔥 {user_data.get('current_calories', 'N/A')} kcal"),
        ("Training Split", f"📅 {user_data.get('workout_split', 'Not specified')}")
    ]
    for title, content in profile_items:
        y_position = pdf.add_info_card(title, content, y_position)
    
    # Force a page break for a fresh start of the workout plan
    pdf.doc.showPage()
    y_position = pdf.add_page_header()  # New page header
    
    # Second page: Workout Section
    y_position = pdf.add_section_title("Workout Plan", y_position, "workout")
    
    # Directly render workout plan without content card
    text_x = pdf.left_margin + 0.4*inch
    text_y = y_position - 0.4*inch
    
    # Split and format the plan text
    lines = plan.split('\n')
    lines = [line.replace('*', '•') for line in lines]
    
    # Calculate available width for text
    available_width = pdf.content_width - 0.8*inch
    text_lines = []
    for line in lines:
        if pdf.doc.stringWidth(line, "Helvetica", 14) > available_width:
            wrapped = simpleSplit(line, "Helvetica", 14, available_width)
            text_lines.extend(wrapped)
        else:
            text_lines.append(line)
    
    line_spacing = 0.3 * inch
    
    # Render content with improved formatting
    for line in text_lines:
        if text_y < pdf.bottom_margin:
            pdf.doc.showPage()
            text_y = pdf.add_page_header() - 1.5*inch
        
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            pdf.doc.setFont("Helvetica-Bold", 14)
            pdf.doc.setFillColor(HexColor('#1E40AF'))
            pdf.doc.drawString(text_x, text_y, parts[0] + ':')
            if len(parts) > 1:
                pdf.doc.setFont("Helvetica", 14)
                pdf.doc.setFillColor(pdf.text_color)
                offset = pdf.doc.stringWidth(parts[0] + ':  ', "Helvetica-Bold", 14)
                pdf.doc.drawString(text_x + offset, text_y, parts[1])
        else:
            pdf.doc.setFont("Helvetica", 14)
            pdf.doc.setFillColor(HexColor('#374151'))
            if line.startswith('•'):
                pdf.doc.setFillColor(pdf.accent_color)
                pdf.doc.circle(text_x - 0.15*inch, text_y + 4, 3, fill=True)
                pdf.doc.setFillColor(HexColor('#374151'))
                pdf.doc.drawString(text_x + 0.1*inch, text_y, line[1:].strip())
            else:
                pdf.doc.drawString(text_x, text_y, line)
        text_y -= line_spacing
    
    # Footer for final page
    pdf.add_footer()
    pdf.doc.save()
    pdf.buffer.seek(0)
    return pdf.buffer

def create_meal_plan_pdf(meal_plan_text, user_data):
    """Generates a Meal Plan PDF using FitTrackerPDF."""
    pdf = FitTrackerPDF("meal")
    y_position = pdf.height - pdf.top_margin
    
    # Header and Nutritional Profile
    y_position = pdf.add_page_header()
    y_position = pdf.add_section_title("Nutritional Profile", y_position, "nutrition")
    
    nutrition_items = [
        ("Goal", f"🎯 {user_data.get('goal', 'Not specified')}"),
        ("Daily Calories", f"🔥 {user_data.get('current_calories', 'N/A')} kcal"),
        ("Current Weight", f"⚖️ {user_data.get('weight', 'N/A')} kg"),
        ("Activity Level", f"💪 {user_data.get('work_type', 'Not specified')}")
    ]
    for title, content in nutrition_items:
        y_position = pdf.add_info_card(title, content, y_position)
    
    # Force a page break for a fresh start of the meal plan
    pdf.doc.showPage()
    y_position = pdf.add_page_header()  # New page header
    
    # Meal Plan Section
    y_position = pdf.add_section_title("Your Meal Plan", y_position, "meal")
    
    # Directly render meal plan without content card
    text_x = pdf.left_margin + 0.4*inch
    text_y = y_position - 0.4*inch
    
    # Split and format the plan text
    lines = meal_plan_text.split('\n')
    lines = [line.replace('*', '•') for line in lines]
    
    # Calculate available width for text
    available_width = pdf.content_width - 0.8*inch
    text_lines = []
    for line in lines:
        if pdf.doc.stringWidth(line, "Helvetica", 14) > available_width:
            wrapped = simpleSplit(line, "Helvetica", 14, available_width)
            text_lines.extend(wrapped)
        else:
            text_lines.append(line)
    
    line_spacing = 0.3 * inch
    
    # Render content with improved formatting
    for line in text_lines:
        if text_y < pdf.bottom_margin:
            pdf.doc.showPage()
            text_y = pdf.add_page_header() - 1.5*inch
        
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            pdf.doc.setFont("Helvetica-Bold", 14)
            pdf.doc.setFillColor(HexColor('#1E40AF'))
            pdf.doc.drawString(text_x, text_y, parts[0] + ':')
            if len(parts) > 1:
                pdf.doc.setFont("Helvetica", 14)
                pdf.doc.setFillColor(pdf.text_color)
                offset = pdf.doc.stringWidth(parts[0] + ':  ', "Helvetica-Bold", 14)
                pdf.doc.drawString(text_x + offset, text_y, parts[1])
        else:
            pdf.doc.setFont("Helvetica", 14)
            pdf.doc.setFillColor(HexColor('#374151'))
            if line.startswith('•'):
                pdf.doc.setFillColor(pdf.accent_color)
                pdf.doc.circle(text_x - 0.15*inch, text_y + 4, 3, fill=True)
                pdf.doc.setFillColor(HexColor('#374151'))
                pdf.doc.drawString(text_x + 0.1*inch, text_y, line[1:].strip())
            else:
                pdf.doc.drawString(text_x, text_y, line)
        text_y -= line_spacing
    
    pdf.add_footer()
    pdf.doc.save()
    pdf.buffer.seek(0)
    return pdf.buffer