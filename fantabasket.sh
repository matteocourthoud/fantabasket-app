# Set src as current directory
ABSPATH="$(dirname "$0")"
cd $ABSPATH/src/

# Prepare data for dashboard
python3 main.py

# Serve dashboard
open http://localhost:8080
python3 dashboard/dashboard.py
