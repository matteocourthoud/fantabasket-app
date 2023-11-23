# Set src as current directory
ABSPATH="$(dirname "$0")"
cd $ABSPATH/src/

# Prepare data for dashboard
python3 main.py

# Kill processes using port 8080
lsof -t -i tcp:8080 | xargs kill

# Serve dashboard
open http://localhost:8080
python3 dashboard/dashboard.py
