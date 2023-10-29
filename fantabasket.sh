# Choose project
cd Dropbox/Projects/Fantabasket

# Scrape games
python3 src/main.py

# Serve dashboard
open http://localhost:8080
python3 src/dashboard/dashboard.py
