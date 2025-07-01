# HomeBrew Management System 

A complete Django-based brewing management system designed for BIAB (Brew-In-A-Bag) home brewing with AI-powered recipe generation.

## Features

- **AI Recipe Generator** - Generate perfect recipes for any batch size using Claude AI or smart formulas
- **📋 Recipe Management** - Create, edit, clone, and scale brewing recipes
- **🧪 Brewing Lab** - Track active brewing sessions with timers and readings
- **📦 Inventory Management** - Track ingredients, costs, and generate shopping lists
- **📊 Analytics** - Monitor brewing performance and efficiency trends
- **🎯 BIAB Optimized** - Strike water calculations, grain absorption, and BIAB-specific workflows

## Quick Start

### Prerequisites
- Python 3.8+
- Django 5.2+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd homebrew-management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver