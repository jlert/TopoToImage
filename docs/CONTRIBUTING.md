# Contributing to TopoToImage 4.0

Thank you for your interest in contributing to TopoToImage! This document provides guidelines for contributing to this recreation of the classic 1990s terrain visualization software.

## 🚀 Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jlert/TopoToImage.git
   cd TopoToImage
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python src/main_window_qt_designer.py
   ```

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and concise

### Testing
- Test your changes with the sample data in `assets/sample_data/`
- Verify cross-platform compatibility when possible
- Ensure UI changes work with Qt Designer files

### File Organization
- **Core logic**: Place in `src/` directory
- **UI files**: Qt Designer files go in `ui/` directory  
- **Assets**: Icons, maps, samples go in `assets/` directory
- **Documentation**: User-facing docs in `docs/` directory

## 🎯 Areas for Contribution

- **Windows/Linux Support** - The application is built with cross-platform libraries (PyQt6) but has only been tested on macOS. We need contributors to test and create installers for Windows and Linux. If you successfully run TopoToImage on Windows or Linux, please document the process and contribute installation instructions!
- **Performance optimization** - Improve rendering speed for large datasets
- **Rendering improvements** - Antialias map images
- **Documentation improvements** - User guides and tutorials

## 📋 Pull Request Process

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding guidelines above
   - Add tests if applicable
   - Update documentation as needed

3. **Test your changes**
   - Verify the application launches correctly
   - Test with sample data
   - Check for any regression issues

4. **Submit pull request**
   - Provide clear description of changes
   - Reference any related issues
   - Include screenshots for UI changes

## 🐛 Bug Reports

When reporting bugs, please include:
- **Operating system** and version
- **Python version**
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Error messages** or logs if available
- **Sample data** if the issue is data-specific

## 💡 Feature Requests

For new features:
- **Describe the use case** and why it's valuable
- **Provide examples** of the desired functionality
- **Consider compatibility** with existing features
- **Reference original TopoToImage** behavior if applicable

## 🗺️ Project Philosophy

TopoToImage 4.0 aims to:
- **Preserve the original's features** while modernizing the implementation
- **Maintain professional cartographic quality**

## 📞 Getting Help

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check the `docs/` directory for detailed guides

---

Thank you for helping to bring this classic cartographic software back to life