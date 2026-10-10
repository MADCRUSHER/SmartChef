# SmartChef — local copy

This package mirrors the public SmartChef Flask architecture:
- Flask backend (`app.py`)
- YOLO-World ingredient detection using `yolov8s-world.pt`
- Spoonacular recipe lookup
- Single-page frontend in `templates/index.html`

## Windows setup

1. Install Python 3.10+.
2. Open PowerShell in this folder.
3. Create and activate a virtual environment:
   `py -m venv .venv`
   `.\.venv\Scripts\Activate.ps1`
4. Install:
   `pip install -r requirements.txt`
5. Put the official `templates/index.html` and `yolov8s-world.pt` in this folder.
   `setup_official_assets.ps1` does that automatically.
6. Set your Spoonacular API key:
   `$env:SPOONACULAR_API_KEY="YOUR_KEY"`
7. Run:
   `python app.py`
8. Open:
   `http://127.0.0.1:5000`

The original public repository contains the frontend and a compressed YOLO model asset.
