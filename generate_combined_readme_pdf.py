#!/usr/bin/env python3
"""
Generate combined README PDF that includes:
1. Installation and Getting Started (from READ ME FIRST.txt)
2. Overview and Features (from existing PDF or README.md if available)
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                KeepTogether, Table, TableStyle)
from reportlab.lib import colors
from datetime import datetime

# Output PDF path
output_path = Path("/Users/josephlertola/Documents/claude-code/topoToimage-dev-workspace/releases/TopoToImage-v4.0.0-beta.3-staging/TopoToImage_README.pdf")

# Create PDF
doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

# Styles
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'Title',
    parent=styles['Heading1'],
    fontSize=28,
    textColor=colors.HexColor('#2C3E50'),
    spaceAfter=10,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

subtitle_style = ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontSize=14,
    textColor=colors.HexColor('#7F8C8D'),
    spaceAfter=30,
    alignment=TA_CENTER
)

heading1_style = ParagraphStyle(
    'Heading1',
    parent=styles['Heading1'],
    fontSize=18,
    textColor=colors.HexColor('#34495E'),
    spaceAfter=12,
    spaceBefore=20,
    fontName='Helvetica-Bold',
    borderWidth=0,
    borderPadding=0,
    borderColor=colors.HexColor('#34495E'),
    borderRadius=0,
    backColor=colors.HexColor('#ECF0F1'),
    leftIndent=10,
    rightIndent=10
)

heading2_style = ParagraphStyle(
    'Heading2',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#16A085'),
    spaceAfter=10,
    spaceBefore=15,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'Body',
    parent=styles['BodyText'],
    fontSize=11,
    leading=16,
    spaceAfter=10
)

bullet_style = ParagraphStyle(
    'Bullet',
    parent=styles['BodyText'],
    fontSize=11,
    leading=16,
    spaceAfter=6,
    leftIndent=20
)

code_style = ParagraphStyle(
    'Code',
    parent=styles['Code'],
    fontSize=10,
    fontName='Courier',
    backColor=colors.HexColor('#F8F9FA'),
    borderColor=colors.HexColor('#DEE2E6'),
    borderWidth=1,
    borderPadding=8,
    leftIndent=10,
    rightIndent=10,
    spaceAfter=12
)

warning_style = ParagraphStyle(
    'Warning',
    parent=styles['BodyText'],
    fontSize=11,
    backColor=colors.HexColor('#FFF3CD'),
    borderColor=colors.HexColor('#FFC107'),
    borderWidth=2,
    borderPadding=10,
    spaceAfter=12
)

# Story
story = []

# Title page
story.append(Spacer(1, 1*inch))
story.append(Paragraph("TopoToImage", title_style))
story.append(Paragraph("v4.0.0-beta.3 for macOS", subtitle_style))
story.append(Paragraph("Professional Terrain Visualization Software", body_style))
story.append(Spacer(1, 0.5*inch))

# Package Contents
story.append(Paragraph("📦 Package Contents", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("• <b>TopoToImage.app</b> - Main application", bullet_style))
story.append(Paragraph("• <b>sample_data/</b> - Sample elevation data for testing", bullet_style))
story.append(Paragraph("• <b>TopoToImage_User_Guide.pdf</b> - Complete user guide with detailed instructions", bullet_style))
story.append(Paragraph("• <b>Elevation_Data_Sources.pdf</b> - Guide to finding elevation data worldwide", bullet_style))
story.append(Paragraph("• <b>TopoToImage_README.pdf</b> - This document (installation and quick start)", bullet_style))
story.append(Spacer(1, 0.2*inch))

# Installation
story.append(Paragraph("🚀 Installation", heading1_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Step 1: Copy the Application</b>", heading2_style))
story.append(Paragraph("Copy <b>TopoToImage.app</b> to your Applications folder (or anywhere you like).", body_style))

story.append(Paragraph("<b>Step 2: First Launch - Bypass macOS Gatekeeper</b>", heading2_style))
story.append(Paragraph("Since TopoToImage is not signed with an Apple Developer certificate, you need to bypass macOS security on first launch:", body_style))

story.append(Paragraph("<b>Method 1 (Recommended):</b>", body_style))
story.append(Paragraph("• Right-click (or Control-click) on TopoToImage.app", bullet_style))
story.append(Paragraph("• Select \"Open\" from the menu", bullet_style))
story.append(Paragraph("• Click \"Open\" in the security dialog", bullet_style))
story.append(Paragraph("• You only need to do this once!", bullet_style))

story.append(Paragraph("<b>Method 2:</b>", body_style))
story.append(Paragraph("• Try to open TopoToImage.app normally", bullet_style))
story.append(Paragraph("• When blocked, go to System Settings → Privacy & Security", bullet_style))
story.append(Paragraph("• Click \"Open Anyway\" next to the TopoToImage message", bullet_style))
story.append(Paragraph("• Enter your password if prompted", bullet_style))

story.append(Paragraph("<b>Step 3: Subsequent Launches</b>", heading2_style))
story.append(Paragraph("After the first launch, the app will work normally by double-clicking.", body_style))
story.append(Spacer(1, 0.2*inch))

# Troubleshooting
story.append(Paragraph("⚠️ Troubleshooting", heading1_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Problem: \"TopoToImage is damaged and can't be opened\"</b>", heading2_style))
story.append(Paragraph("This is a security feature. To fix:", body_style))
story.append(Paragraph("Open Terminal and run:", body_style))
story.append(Paragraph("<font name='Courier'>xattr -cr /Applications/TopoToImage.app</font>", code_style))
story.append(Paragraph("Then try Method 1 above.", body_style))
story.append(Spacer(1, 0.2*inch))

# Getting Started
story.append(PageBreak())
story.append(Paragraph("📖 Getting Started", heading1_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Quick Start - Load Sample Data:</b>", heading2_style))
story.append(Paragraph("1. Open <b>TopoToImage.app</b>", bullet_style))
story.append(Paragraph("2. Click \"<b>Open Single File Database</b>\"", bullet_style))
story.append(Paragraph("3. Navigate to the <b>sample_data</b> folder in this package", bullet_style))
story.append(Paragraph("4. Open \"<b>Gtopo30_reduced_2160x1080_map.tif</b>\"", bullet_style))
story.append(Paragraph("5. Click \"<b>Generate Preview</b>\" to see your first terrain visualization!", bullet_style))
story.append(Paragraph("6. Read <b>TopoToImage_User_Guide.pdf</b> for complete documentation", bullet_style))
story.append(Spacer(1, 0.2*inch))

# Sample Data
story.append(Paragraph("🗺️ Sample Data", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("The included sample_data folder contains:", body_style))
story.append(Paragraph("• Global elevation dataset (2160×1080 pixels)", bullet_style))
story.append(Paragraph("• Perfect for testing all features", bullet_style))
story.append(Paragraph("• Covers the entire world", bullet_style))
story.append(Spacer(1, 0.2*inch))

# Where to Get More Data
story.append(Paragraph("📊 Where to Get More Data", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("See <b>Elevation_Data_Sources.pdf</b> for:", body_style))
story.append(Paragraph("• Free global elevation datasets (SRTM, GTOPO30, GEBCO)", bullet_style))
story.append(Paragraph("• Regional high-resolution data sources", bullet_style))
story.append(Paragraph("• Data preparation tips", bullet_style))
story.append(Spacer(1, 0.2*inch))

# What's New
story.append(PageBreak())
story.append(Paragraph("✨ What's New in Beta.3", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("• <b>Fixed:</b> Export elevation database feature now works correctly in bundled app", bullet_style))
story.append(Paragraph("• <b>Fixed:</b> Multi-file database export issue resolved", bullet_style))
story.append(Paragraph("• <b>Improved:</b> Optimized debug logging for better performance", bullet_style))
story.append(Paragraph("• <b>Improved:</b> File dialog paths now use home directory by default", bullet_style))
story.append(Spacer(1, 0.3*inch))

# Features Overview
story.append(Paragraph("🎨 Key Features", heading1_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Terrain Rendering:</b>", heading2_style))
story.append(Paragraph("• Multiple shading methods (hillshade, slope, aspect, curvature)", bullet_style))
story.append(Paragraph("• Customizable color gradients with built-in and custom options", bullet_style))
story.append(Paragraph("• Real-time preview with interactive controls", bullet_style))
story.append(Paragraph("• Unlimited shading intensity", bullet_style))

story.append(Paragraph("<b>Data Support:</b>", heading2_style))
story.append(Paragraph("• Single-file databases (GeoTIFF format)", bullet_style))
story.append(Paragraph("• Multi-file databases (tile-based elevation data)", bullet_style))
story.append(Paragraph("• Export to GeoTIFF format", bullet_style))
story.append(Paragraph("• Support for various coordinate systems", bullet_style))

story.append(Paragraph("<b>Export Options:</b>", heading2_style))
story.append(Paragraph("• High-resolution image export (PNG, JPEG, TIFF)", bullet_style))
story.append(Paragraph("• GeoTIFF export with full georeferencing", bullet_style))
story.append(Paragraph("• Elevation database export for selected regions", bullet_style))
story.append(Paragraph("• Customizable export scale and quality", bullet_style))
story.append(Spacer(1, 0.3*inch))

# Bug Reports
story.append(Paragraph("🐛 Report Bugs", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Found an issue? Report it at:", body_style))
story.append(Paragraph("<link href='https://github.com/jlert/TopoToImage/issues'>https://github.com/jlert/TopoToImage/issues</link>", code_style))
story.append(Spacer(1, 0.3*inch))

# License
story.append(Paragraph("📄 License", heading1_style))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("TopoToImage is released under the MIT License", body_style))
story.append(Paragraph("Copyright © 2025 Joseph Lertola", body_style))
story.append(Spacer(1, 0.5*inch))

# Footer
story.append(Paragraph("═" * 80, body_style))
story.append(Paragraph("Thank you for using TopoToImage!", subtitle_style))
story.append(Paragraph("═" * 80, body_style))

# Build PDF
doc.build(story)

print(f"✅ Generated combined README PDF: {output_path}")
print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
