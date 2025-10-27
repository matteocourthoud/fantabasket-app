# 🏀 Fantabasket Analytics

A comprehensive fantasy basketball analytics platform that scrapes NBA statistics, computes fantasy basketball scores and player valuations, and presents them in an interactive Streamlit dashboard.

## Features

- 📊 Real-time NBA statistics scraping from multiple sources
- 🧮 Advanced fantasy basketball score computation
- 📈 Player valuation and performance tracking
- 🤕 Injury status monitoring
- 📱 Interactive Streamlit dashboard
- 🗄️ Supabase database integration

## Getting Started

### Prerequisites

- Python 3.13+
- Chrome/Chromium (for web scraping)
- Supabase account (for data storage)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/matteocourthoud/fantabasket-app.git
   cd fantabasket-app
   ```

2. Set up the environment:
   ```bash
   make install-deps
   ```

3. Configure Supabase:
   - Create a `.streamlit/secrets.toml` file with your Supabase credentials:
     ```toml
     [connections.supabase]
     SUPABASE_URL = "your-project-url"
     SUPABASE_KEY = "your-anon-key"
     ```

### Running the App

Launch the Streamlit dashboard:
```bash
make run-app
```

## Project Structure

```
src/
├── scraping/          # Web scraping scripts
├── stats/            # Statistics computation
├── streamlit/        # Streamlit dashboard
└── supabase/         # Database utilities
```

## Features in Detail

### Data Collection
- NBA game statistics from Basketball Reference
- Player ratings from Dunkest
- Starting lineups (updated daily)
- Injury reports

### Analytics
- Fantasy basketball score computation
- Player value tracking
- Performance predictions
- Team correlation analysis

### Dashboard Views
- Player statistics with filtering
- Individual player performance analysis
- Injury tracking
- Custom visualization options

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Data sourced from Basketball Reference and Dunkest
- Built with Streamlit and Supabase
- Inspired by fantasy basketball enthusiasts
