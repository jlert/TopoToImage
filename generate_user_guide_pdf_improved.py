#!/usr/bin/env python3
"""
Generate User Guide PDF from Markdown with:
- Proper image aspect ratios
- Working table of contents with links
- Darker, readable heading colors
- Properly formatted code blocks and folder structures
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                PageBreak, Table, TableStyle, KeepTogether,
                                Preformatted, ListFlowable, ListItem)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
from PIL import Image as PILImage

# Read the USER_GUIDE.md file
user_guide_path = Path("docs/USER_GUIDE.md")
with open(user_guide_path, 'r') as f:
    content = f.read()

# Output PDF path
output_path = Path("/Users/josephlertola/Documents/claude-code/topoToimage-dev-workspace/releases/TopoToImage-v4.0.0-beta.3-staging/TopoToImage_User_Guide.pdf")

# Create PDF with bookmarks enabled
doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

# Styles with DARKER colors for better readability
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1A1A1A'),  # Much darker
    spaceAfter=10,  # Reduced from 30
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading1_style = ParagraphStyle(
    'CustomHeading1',
    parent=styles['Heading1'],
    fontSize=16,
    textColor=colors.HexColor('#2C3E50'),  # Dark blue-gray
    spaceAfter=6,  # Reduced from 8
    spaceBefore=8,  # Reduced from 12
    keepWithNext=True,
    fontName='Helvetica-Bold'
)

heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontSize=13,
    textColor=colors.HexColor('#34495E'),  # Darker blue-gray
    spaceAfter=4,  # Reduced from 6
    spaceBefore=6,  # Reduced from 10
    keepWithNext=True,
    fontName='Helvetica-Bold'
)

heading3_style = ParagraphStyle(
    'CustomHeading3',
    parent=styles['Heading3'],
    fontSize=11,
    textColor=colors.HexColor('#5D6D7E'),  # Medium gray (darker than before)
    spaceAfter=3,  # Reduced from 4
    spaceBefore=5,  # Reduced from 8
    keepWithNext=True,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=10,
    leading=12,  # Reduced from 13
    spaceAfter=2,  # Reduced from 4
    alignment=TA_JUSTIFY
)

code_style = ParagraphStyle(
    'CustomCode',
    parent=styles['Code'],
    fontSize=9,
    fontName='Courier',
    textColor=colors.HexColor('#2C3E50'),
    backColor=colors.HexColor('#F8F9FA'),
    borderColor=colors.HexColor('#DEE2E6'),
    borderWidth=1,
    borderPadding=8,
    leftIndent=20,
    rightIndent=20,
    spaceAfter=10,
    leading=12
)

toc_heading_style = ParagraphStyle(
    'TOCHeading',
    parent=heading1_style,
    fontSize=18,
    spaceAfter=20
)

toc_entry_style = ParagraphStyle(
    'TOCEntry',
    parent=body_style,
    fontSize=10,
    leading=13,  # Tighter spacing
    leftIndent=0,
    spaceAfter=2  # Reduced from 4
)

# Story (content list)
story = []

# Add title
story.append(Paragraph("TopoToImage User Guide", title_style))
story.append(Paragraph(f"Version 4.0.0-beta.3 | {datetime.now().strftime('%B %Y')}", body_style))
story.append(Spacer(1, 0.1*inch))

# Add banner image
banner_path = Path("docs/images/banner_image.png")
if banner_path.exists():
    try:
        with PILImage.open(banner_path) as pil_img:
            img_width, img_height = pil_img.size
            aspect_ratio = img_width / img_height

        # Banner width - use full page width
        banner_display_width = 6 * inch
        banner_display_height = banner_display_width / aspect_ratio

        banner_img = Image(str(banner_path), width=banner_display_width, height=banner_display_height)
        story.append(banner_img)
        story.append(Spacer(1, 0.15*inch))
    except Exception as e:
        print(f"Warning: Could not load banner image: {e}")

story.append(Spacer(1, 0.1*inch))

# Extract sections for table of contents
sections = []
lines = content.split('\n')

# Parse for h2 sections (##)
for i, line in enumerate(lines):
    if line.startswith('## ') and not line.startswith('## Table of Contents'):
        section_title = line[3:].strip()
        # Create anchor name
        anchor = section_title.lower().replace(' ', '_').replace('/', '_')
        sections.append((section_title, anchor))

# Build Table of Contents
story.append(Paragraph("Table of Contents", toc_heading_style))
story.append(Spacer(1, 0.1*inch))

for idx, (title, anchor) in enumerate(sections, 1):
    toc_text = f'<a href="#{anchor}" color="blue">{idx}. {title}</a>'
    story.append(Paragraph(toc_text, toc_entry_style))

# Add spacer before content starts (no PageBreak to avoid blank page)
story.append(Spacer(1, 0.15*inch))

# Parse markdown content
i = 0
in_code_block = False
code_block_content = []
current_section = None
skip_toc_section = False

while i < len(lines):
    line = lines[i]

    # Skip the title and version (already added)
    if i < 5:
        i += 1
        continue

    # Skip entire Table of Contents section from markdown
    if line.strip() == '## Table of Contents':
        skip_toc_section = True
        i += 1
        continue

    # End of TOC section when we hit the next ## heading or ---
    if skip_toc_section and (line.startswith('## ') or line.strip() == '---'):
        skip_toc_section = False
        if line.strip() == '---':
            i += 1
            continue
        # Don't skip this line, process it normally

    # Skip lines within TOC section
    if skip_toc_section:
        i += 1
        continue

    # Code blocks
    if line.strip().startswith('```'):
        if in_code_block:
            # End of code block - format as preformatted text
            code_text = '\n'.join(code_block_content)
            # Use Preformatted for better code block formatting
            pre = Preformatted(code_text, code_style)
            story.append(pre)
            code_block_content = []
            in_code_block = False
        else:
            # Start of code block
            in_code_block = True
        i += 1
        continue

    if in_code_block:
        code_block_content.append(line)
        i += 1
        continue

    # Images - preserve aspect ratio
    if line.strip().startswith('!['):
        # Extract image path: ![alt text](path)
        match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line.strip())
        if match:
            img_path = Path("docs") / match.group(2)
            if img_path.exists():
                try:
                    # Get actual image dimensions using PIL
                    with PILImage.open(img_path) as pil_img:
                        img_width, img_height = pil_img.size
                        aspect_ratio = img_width / img_height

                    # Set max width to 6 inches
                    max_width = 6 * inch
                    # Calculate height to maintain aspect ratio
                    if aspect_ratio > 1:  # Wider than tall
                        img_display_width = min(max_width, 6*inch)
                        img_display_height = img_display_width / aspect_ratio
                    else:  # Taller than wide
                        img_display_height = 4 * inch
                        img_display_width = img_display_height * aspect_ratio

                    img = Image(str(img_path), width=img_display_width, height=img_display_height)
                    story.append(img)
                    story.append(Spacer(1, 0.05*inch))  # Reduced from 0.1
                except Exception as e:
                    print(f"Warning: Could not load image {img_path}: {e}")
        i += 1
        continue

    # Horizontal rules
    if line.strip() == '---':
        story.append(Spacer(1, 0.03*inch))  # Reduced from 0.05
        i += 1
        continue

    # Headings with anchors
    if line.startswith('## ') and not line.startswith('## Table of Contents'):
        section_title = line[3:].strip()
        anchor = section_title.lower().replace(' ', '_').replace('/', '_')
        # Add larger spacer instead of PageBreak to avoid blank pages
        story.append(Spacer(1, 0.2*inch))
        # Add bookmark for internal links
        story.append(Paragraph(f'<a name="{anchor}"/>{section_title}', heading1_style))
        current_section = section_title
        i += 1
        continue
    elif line.startswith('### '):
        story.append(Paragraph(line[4:], heading2_style))
        i += 1
        continue
    elif line.startswith('#### '):
        story.append(Paragraph(line[5:], heading3_style))
        i += 1
        continue

    # Bullet lists
    if line.strip().startswith('- ') or line.strip().startswith('* '):
        bullet_text = line.strip()[2:]
        # Convert markdown bold **text** to <b>text</b>
        bullet_text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', bullet_text)
        # Convert markdown italic *text* to <i>text</i>
        bullet_text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', bullet_text)
        story.append(Paragraph(f"• {bullet_text}", body_style))
        i += 1
        continue

    # Numbered lists
    if re.match(r'^\d+\.\s', line.strip()):
        list_text = re.sub(r'^\d+\.\s', '', line.strip())
        # Convert markdown formatting
        list_text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', list_text)
        list_text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', list_text)

        # Extract number
        num = re.match(r'^(\d+)\.', line.strip()).group(1)
        story.append(Paragraph(f"{num}. {list_text}", body_style))
        i += 1
        continue

    # Regular paragraphs
    if line.strip() and not line.strip().startswith('#'):
        # Convert markdown bold **text** to <b>text</b>
        processed_line = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', line)
        # Convert markdown italic *text* to <i>text</i>
        processed_line = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', processed_line)
        # Convert markdown links [text](url) to clickable links
        processed_line = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<link href="\2">\1</link>', processed_line)

        story.append(Paragraph(processed_line, body_style))
    elif not line.strip():
        story.append(Spacer(1, 0.03*inch))  # Reduced from 0.05

    i += 1

# Build PDF
doc.build(story)

print(f"✅ Generated User Guide PDF: {output_path}")
print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
print("   ✓ Images preserve aspect ratios")
print("   ✓ Table of contents with working links")
print("   ✓ Darker, more readable heading colors")
print("   ✓ Properly formatted code blocks")
