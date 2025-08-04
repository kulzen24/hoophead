# HoopHead Integration Guide

## Overview

This guide provides comprehensive patterns and best practices for integrating HoopHead into various types of applications. Whether you're building a web application, mobile app, data analysis platform, or CLI tool, this guide covers the essential integration patterns.

## Table of Contents

- [Integration Strategies](#integration-strategies)
- [Web Application Integration](#web-application-integration)
- [Data Analysis Integration](#data-analysis-integration)
- [Real-time Applications](#real-time-applications)
- [Batch Processing](#batch-processing)
- [Mobile App Integration](#mobile-app-integration)
- [Microservices Architecture](#microservices-architecture)
- [Performance Optimization](#performance-optimization)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Observability](#monitoring-and-observability)

## Integration Strategies

### 1. Direct Client Integration

Best for: Simple applications, prototypes, small-scale usage

```python
from backend.src.adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

# Simple direct integration
async def get_team_stats():
    async with BallDontLieClient() as client:
        teams = await client.get_teams(Sport.NBA)
        return teams.data

# Pros: Simple, minimal setup
# Cons: No advanced features, limited scalability
```

### 2. Service Layer Integration

Best for: Medium to large applications, business logic separation

```python
from backend.src.domain.services.team_service import TeamService
from backend.src.domain.services.player_service import PlayerService

class SportsDataService:
    """High-level sports data service."""
    
    def __init__(self, api_key: str):
        self.client = BallDontLieClient(api_key=api_key)
        self.team_service = TeamService(self.client)
        self.player_service = PlayerService(self.client)
    
    async def get_team_roster(self, team_id: int, sport: Sport) -> List[Player]:
        """Get complete team roster with enhanced data."""
        return await self.team_service.get_team_roster(team_id, sport)
    
    async def compare_players(self, player1_id: int, player2_id: int, sport: Sport) -> Dict:
        """Compare two players with statistical analysis."""
        return await self.player_service.compare_players(player1_id, player2_id, sport)

# Pros: Clean separation, business logic, testable
# Cons: More complex setup
```

### 3. Repository Pattern Integration

Best for: Complex applications, data persistence, testing

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class SportsDataRepository(ABC):
    """Abstract repository for sports data."""
    
    @abstractmethod
    async def get_teams(self, sport: Sport) -> List[Team]:
        pass
    
    @abstractmethod
    async def get_player(self, player_id: int, sport: Sport) -> Optional[Player]:
        pass

class HoopHeadRepository(SportsDataRepository):
    """HoopHead implementation of sports data repository."""
    
    def __init__(self, client: BallDontLieClient):
        self.client = client
    
    async def get_teams(self, sport: Sport) -> List[Team]:
        response = await self.client.get_teams(sport)
        return [Team.from_api_response(team_data, sport) for team_data in response.data['data']]
    
    async def get_player(self, player_id: int, sport: Sport) -> Optional[Player]:
        # Implementation with error handling and caching
        pass

# Pros: Testable, mockable, swappable implementations
# Cons: Most complex to set up
```

## Web Application Integration

### FastAPI Integration

Complete web API implementation:

```python
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio

app = FastAPI(title="HoopHead Sports API", version="1.0.0")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global client instance with connection pooling
client = BallDontLieClient()

# Dependency injection for client
async def get_sports_client() -> BallDontLieClient:
    return client

# Request/Response models
class TeamResponse(BaseModel):
    id: int
    name: str
    full_name: str
    city: str
    abbreviation: str
    conference: Optional[str]
    division: Optional[str]

class PlayerSearchRequest(BaseModel):
    search: str
    sport: str
    limit: int = 25

class PlayerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: Optional[str]
    team: Optional[dict]
    height: Optional[str]
    weight: Optional[str]

# API Endpoints
@app.get("/api/sports")
async def get_supported_sports():
    """Get list of supported sports."""
    return {
        "sports": [
            {"code": "nba", "name": "National Basketball Association"},
            {"code": "mlb", "name": "Major League Baseball"},
            {"code": "nfl", "name": "National Football League"},
            {"code": "nhl", "name": "National Hockey League"},
            {"code": "epl", "name": "English Premier League"}
        ]
    }

@app.get("/api/{sport}/teams", response_model=List[TeamResponse])
async def get_teams(sport: str, client: BallDontLieClient = Depends(get_sports_client)):
    """Get all teams for a sport."""
    try:
        sport_enum = Sport(sport.lower())
        response = await client.get_teams(sport_enum)
        teams = response.data['data']
        
        return [TeamResponse(**team) for team in teams]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/{sport}/players/search", response_model=List[PlayerResponse])
async def search_players(
    sport: str, 
    request: PlayerSearchRequest,
    client: BallDontLieClient = Depends(get_sports_client)
):
    """Search players in a sport."""
    try:
        sport_enum = Sport(sport.lower())
        response = await client.get_players(
            sport_enum, 
            search=request.search, 
            per_page=request.limit
        )
        players = response.data['data']
        
        return [PlayerResponse(**player) for player in players]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{sport}/games")
async def get_games(
    sport: str,
    team_id: Optional[int] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    client: BallDontLieClient = Depends(get_sports_client)
):
    """Get games with filtering options."""
    try:
        sport_enum = Sport(sport.lower())
        
        # Build filter parameters
        params = {"page": page, "per_page": 25}
        if team_id:
            params["team_ids"] = [team_id]
        if season:
            params["seasons"] = [season]
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = await client.get_games(sport_enum, **params)
        
        return {
            "games": response.data['data'],
            "pagination": response.data['meta']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task for cache warming
@app.post("/api/admin/warm-cache")
async def warm_cache(background_tasks: BackgroundTasks):
    """Warm cache with popular queries."""
    
    async def warm_cache_task():
        popular_players = ["LeBron", "Curry", "Durant", "Mahomes", "Ohtani"]
        sports = [Sport.NBA, Sport.NFL, Sport.MLB]
        
        for sport in sports:
            # Warm teams cache
            await client.get_teams(sport)
            
            # Warm popular players cache
            for player in popular_players:
                try:
                    await client.get_players(sport, search=player)
                except:
                    pass  # Continue if player not found in sport
    
    background_tasks.add_task(warm_cache_task)
    return {"message": "Cache warming started"}

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test API connectivity
        response = await client.get_teams(Sport.NBA)
        return {
            "status": "healthy",
            "api_connection": "ok",
            "cache_enabled": client.cache_enabled
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application."""
    print("HoopHead API starting up...")
    # Pre-warm cache with popular data
    await warm_cache_task()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    await client.close()
    print("HoopHead API shut down")

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

### Next.js Frontend Integration

React/TypeScript frontend implementation:

```typescript
// lib/hoophead-api.ts
interface TeamData {
  id: number;
  name: string;
  full_name: string;
  city: string;
  abbreviation: string;
  conference?: string;
  division?: string;
}

interface PlayerData {
  id: number;
  first_name: string;
  last_name: string;
  position?: string;
  team?: any;
  height?: string;
  weight?: string;
}

interface GameData {
  id: number;
  date: string;
  home_team: any;
  visitor_team: any;
  home_team_score: number;
  visitor_team_score: number;
  status: string;
}

class HoopHeadAPI {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000/api') {
    this.baseUrl = baseUrl;
  }

  async getTeams(sport: string): Promise<TeamData[]> {
    const response = await fetch(`${this.baseUrl}/${sport}/teams`);
    if (!response.ok) {
      throw new Error(`Failed to fetch teams: ${response.statusText}`);
    }
    return response.json();
  }

  async searchPlayers(sport: string, search: string, limit: number = 25): Promise<PlayerData[]> {
    const response = await fetch(`${this.baseUrl}/${sport}/players/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ search, sport, limit }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to search players: ${response.statusText}`);
    }
    return response.json();
  }

  async getGames(sport: string, options: {
    teamId?: number;
    season?: number;
    startDate?: string;
    endDate?: string;
    page?: number;
  } = {}): Promise<{ games: GameData[]; pagination: any }> {
    const params = new URLSearchParams();
    
    if (options.teamId) params.append('team_id', options.teamId.toString());
    if (options.season) params.append('season', options.season.toString());
    if (options.startDate) params.append('start_date', options.startDate);
    if (options.endDate) params.append('end_date', options.endDate);
    if (options.page) params.append('page', options.page.toString());

    const response = await fetch(`${this.baseUrl}/${sport}/games?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch games: ${response.statusText}`);
    }
    return response.json();
  }
}

export const hoopheadApi = new HoopHeadAPI();
export type { TeamData, PlayerData, GameData };
```

```tsx
// components/TeamsList.tsx
import React, { useState, useEffect } from 'react';
import { hoopheadApi, TeamData } from '../lib/hoophead-api';

interface TeamsListProps {
  sport: string;
}

const TeamsList: React.FC<TeamsListProps> = ({ sport }) => {
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setLoading(true);
        setError(null);
        const teamsData = await hoopheadApi.getTeams(sport);
        setTeams(teamsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load teams');
      } finally {
        setLoading(false);
      }
    };

    fetchTeams();
  }, [sport]);

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <p className="text-red-800">Error loading teams: {error}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
      {teams.map((team) => (
        <div key={team.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
          <h3 className="text-lg font-semibold text-gray-900">{team.full_name}</h3>
          <p className="text-gray-600">{team.city}</p>
          <div className="mt-2 flex justify-between items-center">
            <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
              {team.abbreviation}
            </span>
            {team.conference && (
              <span className="text-sm text-gray-500">{team.conference}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TeamsList;
```

```tsx
// components/PlayerSearch.tsx
import React, { useState, useCallback } from 'react';
import { hoopheadApi, PlayerData } from '../lib/hoophead-api';
import { debounce } from 'lodash';

interface PlayerSearchProps {
  sport: string;
}

const PlayerSearch: React.FC<PlayerSearchProps> = ({ sport }) => {
  const [query, setQuery] = useState('');
  const [players, setPlayers] = useState<PlayerData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchPlayers = useCallback(
    debounce(async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setPlayers([]);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const results = await hoopheadApi.searchPlayers(sport, searchQuery, 10);
        setPlayers(results);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Search failed');
        setPlayers([]);
      } finally {
        setLoading(false);
      }
    }, 300),
    [sport]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    searchPlayers(value);
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          placeholder={`Search ${sport.toUpperCase()} players...`}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {loading && (
          <div className="absolute right-3 top-2.5">
            <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-2 text-red-600 text-sm">{error}</div>
      )}

      {players.length > 0 && (
        <div className="mt-4 bg-white border border-gray-200 rounded-lg shadow-lg">
          {players.map((player) => (
            <div key={player.id} className="p-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="font-medium text-gray-900">
                    {player.first_name} {player.last_name}
                  </h4>
                  {player.team && (
                    <p className="text-sm text-gray-600">{player.team.full_name}</p>
                  )}
                </div>
                <div className="text-right">
                  {player.position && (
                    <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                      {player.position}
                    </span>
                  )}
                  {player.height && (
                    <p className="text-xs text-gray-500 mt-1">{player.height}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PlayerSearch;
```

## Data Analysis Integration

### Pandas Integration

Comprehensive data analysis setup:

```python
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta

class SportsDataAnalyzer:
    """Advanced sports data analysis using pandas."""
    
    def __init__(self, api_key: str):
        self.client = BallDontLieClient(api_key=api_key)
    
    async def get_teams_dataframe(self, sport: Sport) -> pd.DataFrame:
        """Get teams as a pandas DataFrame with enhanced features."""
        response = await self.client.get_teams(sport)
        teams_data = response.data['data']
        
        df = pd.DataFrame(teams_data)
        
        # Add computed columns
        df['sport'] = sport.value
        df['full_location'] = df['city'] + ', ' + df['name']
        df['conference_division'] = df['conference'].fillna('') + ' - ' + df['division'].fillna('')
        
        return df
    
    async def get_all_sports_teams(self) -> pd.DataFrame:
        """Get teams from all sports in a single DataFrame."""
        all_teams = []
        sports = [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL]
        
        for sport in sports:
            try:
                sport_teams = await self.get_teams_dataframe(sport)
                all_teams.append(sport_teams)
            except Exception as e:
                print(f"Error fetching {sport.value} teams: {e}")
        
        if all_teams:
            combined_df = pd.concat(all_teams, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()
    
    async def analyze_league_structure(self, sport: Sport) -> Dict[str, any]:
        """Analyze league structure and distribution."""
        df = await self.get_teams_dataframe(sport)
        
        analysis = {
            'total_teams': len(df),
            'conferences': df['conference'].value_counts().to_dict() if 'conference' in df.columns else {},
            'divisions': df['division'].value_counts().to_dict() if 'division' in df.columns else {},
            'cities': len(df['city'].unique()),
            'most_teams_city': df['city'].value_counts().head(1).to_dict(),
            'team_distribution': {
                'by_conference': df.groupby('conference').size().to_dict() if 'conference' in df.columns else {},
                'by_division': df.groupby('division').size().to_dict() if 'division' in df.columns else {}
            }
        }
        
        return analysis
    
    async def get_players_analysis(self, sport: Sport, sample_size: int = 1000) -> pd.DataFrame:
        """Get a representative sample of players for analysis."""
        all_players = []
        page = 1
        per_page = 100
        
        while len(all_players) < sample_size:
            try:
                response = await self.client.get_players(sport, page=page, per_page=per_page)
                players = response.data['data']
                
                if not players:
                    break
                
                all_players.extend(players)
                page += 1
                
                # Respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching players on page {page}: {e}")
                break
        
        # Limit to requested sample size
        all_players = all_players[:sample_size]
        
        df = pd.DataFrame(all_players)
        
        # Clean and enhance data
        if 'height' in df.columns:
            df['height_inches'] = df['height'].apply(self._parse_height)
        if 'weight' in df.columns:
            df['weight_lbs'] = pd.to_numeric(df['weight'], errors='coerce')
        
        # Add team information
        if 'team' in df.columns:
            df['team_name'] = df['team'].apply(lambda x: x.get('full_name', '') if x else '')
            df['team_city'] = df['team'].apply(lambda x: x.get('city', '') if x else '')
            df['team_conference'] = df['team'].apply(lambda x: x.get('conference', '') if x else '')
        
        return df
    
    def _parse_height(self, height_str: str) -> Optional[int]:
        """Parse height string (e.g., '6-6') to total inches."""
        if not height_str or pd.isna(height_str):
            return None
        
        try:
            if '-' in height_str:
                feet, inches = height_str.split('-')
                return int(feet) * 12 + int(inches)
        except:
            pass
        return None
    
    async def compare_sports_metrics(self) -> pd.DataFrame:
        """Compare key metrics across all sports."""
        sports_data = []
        
        for sport in [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL]:
            try:
                teams_df = await self.get_teams_dataframe(sport)
                players_df = await self.get_players_analysis(sport, 200)
                
                sport_metrics = {
                    'sport': sport.value,
                    'total_teams': len(teams_df),
                    'conferences': teams_df['conference'].nunique() if 'conference' in teams_df.columns else 0,
                    'divisions': teams_df['division'].nunique() if 'division' in teams_df.columns else 0,
                    'sample_players': len(players_df),
                    'avg_height_inches': players_df['height_inches'].mean() if 'height_inches' in players_df.columns else None,
                    'avg_weight_lbs': players_df['weight_lbs'].mean() if 'weight_lbs' in players_df.columns else None,
                    'international_player_pct': (
                        (players_df['country'] != 'USA').sum() / len(players_df) * 100 
                        if 'country' in players_df.columns and len(players_df) > 0 else None
                    )
                }
                
                sports_data.append(sport_metrics)
                
            except Exception as e:
                print(f"Error analyzing {sport.value}: {e}")
        
        return pd.DataFrame(sports_data)

# Usage example
async def run_comprehensive_analysis():
    """Run comprehensive sports data analysis."""
    analyzer = SportsDataAnalyzer("your-api-key")
    
    # Get all teams across sports
    print("Fetching teams data...")
    all_teams = await analyzer.get_all_sports_teams()
    print(f"Total teams across all sports: {len(all_teams)}")
    
    # Analyze each sport individually
    for sport in [Sport.NBA, Sport.MLB, Sport.NFL]:
        print(f"\nAnalyzing {sport.value.upper()}...")
        
        league_analysis = await analyzer.analyze_league_structure(sport)
        print(f"  Teams: {league_analysis['total_teams']}")
        print(f"  Conferences: {list(league_analysis['conferences'].keys())}")
        print(f"  Divisions: {len(league_analysis['divisions'])}")
    
    # Compare sports metrics
    print("\nComparing sports metrics...")
    comparison = await analyzer.compare_sports_metrics()
    print(comparison.to_string(index=False))
    
    # Save results
    all_teams.to_csv('all_sports_teams.csv', index=False)
    comparison.to_csv('sports_comparison.csv', index=False)
    print("\nData saved to CSV files")

# Run the analysis
if __name__ == "__main__":
    asyncio.run(run_comprehensive_analysis())
```

### Jupyter Notebook Integration

Complete notebook setup for data science workflows:

```python
# sports_analysis.ipynb

# Cell 1: Setup and imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import asyncio
from IPython.display import display, HTML
import warnings
warnings.filterwarnings('ignore')

# Configure plotting
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Import HoopHead
import sys
sys.path.append('../backend/src')
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport

# Initialize client
client = BallDontLieClient()

# Cell 2: Helper functions for notebook
async def fetch_and_cache_data(sport, data_type='teams'):
    """Fetch data and cache locally for notebook use."""
    cache_file = f"{sport.value}_{data_type}.csv"
    
    try:
        # Try to load from cache first
        return pd.read_csv(cache_file)
    except FileNotFoundError:
        # Fetch from API
        if data_type == 'teams':
            response = await client.get_teams(sport)
            data = response.data['data']
        elif data_type == 'players':
            all_players = []
            for page in range(1, 6):  # First 500 players
                response = await client.get_players(sport, page=page, per_page=100)
                players = response.data['data']
                if not players:
                    break
                all_players.extend(players)
                await asyncio.sleep(0.1)  # Rate limiting
            data = all_players
        
        df = pd.DataFrame(data)
        df.to_csv(cache_file, index=False)
        return df

def plot_team_distribution(teams_df, sport_name):
    """Plot team distribution by conference/division."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Conference distribution
    if 'conference' in teams_df.columns:
        conference_counts = teams_df['conference'].value_counts()
        axes[0].pie(conference_counts.values, labels=conference_counts.index, autopct='%1.1f%%')
        axes[0].set_title(f'{sport_name} Teams by Conference')
    
    # Division distribution
    if 'division' in teams_df.columns:
        division_counts = teams_df['division'].value_counts()
        axes[1].barh(division_counts.index, division_counts.values)
        axes[1].set_title(f'{sport_name} Teams by Division')
        axes[1].set_xlabel('Number of Teams')
    
    plt.tight_layout()
    plt.show()

# Cell 3: NBA Analysis
print("🏀 NBA Analysis")
print("=" * 50)

nba_teams = await fetch_and_cache_data(Sport.NBA, 'teams')
print(f"Total NBA teams: {len(nba_teams)}")

# Display sample data
display(nba_teams.head())

# Plot distributions
plot_team_distribution(nba_teams, 'NBA')

# Conference analysis
conference_analysis = nba_teams.groupby('conference').agg({
    'id': 'count',
    'city': lambda x: ', '.join(x[:3])  # Show first 3 cities
}).rename(columns={'id': 'team_count', 'city': 'sample_cities'})

print("\nNBA Conference Breakdown:")
display(conference_analysis)

# Cell 4: Multi-sport comparison
print("🏆 Multi-Sport Comparison")
print("=" * 50)

sports_summary = []

for sport in [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL]:
    teams_df = await fetch_and_cache_data(sport, 'teams')
    
    summary = {
        'Sport': sport.value.upper(),
        'Total Teams': len(teams_df),
        'Conferences': teams_df['conference'].nunique() if 'conference' in teams_df.columns else 0,
        'Divisions': teams_df['division'].nunique() if 'division' in teams_df.columns else 0,
        'Unique Cities': teams_df['city'].nunique()
    }
    sports_summary.append(summary)

comparison_df = pd.DataFrame(sports_summary)
display(comparison_df)

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Teams by sport
axes[0,0].bar(comparison_df['Sport'], comparison_df['Total Teams'])
axes[0,0].set_title('Total Teams by Sport')
axes[0,0].set_ylabel('Number of Teams')

# Conferences by sport
axes[0,1].bar(comparison_df['Sport'], comparison_df['Conferences'])
axes[0,1].set_title('Conferences by Sport')
axes[0,1].set_ylabel('Number of Conferences')

# Divisions by sport
axes[1,0].bar(comparison_df['Sport'], comparison_df['Divisions'])
axes[1,0].set_title('Divisions by Sport')
axes[1,0].set_ylabel('Number of Divisions')

# Cities by sport
axes[1,1].bar(comparison_df['Sport'], comparison_df['Unique Cities'])
axes[1,1].set_title('Unique Cities by Sport')
axes[1,1].set_ylabel('Number of Cities')

plt.tight_layout()
plt.show()

# Cell 5: Player analysis (if you have access)
print("👥 Player Analysis Sample")
print("=" * 50)

# Note: This requires appropriate API tier
try:
    nba_players = await fetch_and_cache_data(Sport.NBA, 'players')
    
    if len(nba_players) > 0:
        print(f"NBA players sample: {len(nba_players)}")
        
        # Position distribution
        if 'position' in nba_players.columns:
            position_counts = nba_players['position'].value_counts()
            
            plt.figure(figsize=(10, 6))
            position_counts.plot(kind='bar')
            plt.title('NBA Player Position Distribution')
            plt.xlabel('Position')
            plt.ylabel('Number of Players')
            plt.xticks(rotation=45)
            plt.show()
        
        # Team distribution
        if 'team' in nba_players.columns:
            # Extract team names
            nba_players['team_name'] = nba_players['team'].apply(
                lambda x: x.get('abbreviation', 'N/A') if isinstance(x, dict) else 'N/A'
            )
            
            team_player_counts = nba_players['team_name'].value_counts().head(10)
            
            plt.figure(figsize=(12, 6))
            team_player_counts.plot(kind='bar')
            plt.title('Top 10 Teams by Player Count (Sample)')
            plt.xlabel('Team')
            plt.ylabel('Players in Sample')
            plt.xticks(rotation=45)
            plt.show()
        
        display(nba_players.head())
    
except Exception as e:
    print(f"Player data requires higher API tier: {e}")

# Cell 6: Cache management and cleanup
print("💾 Cache Management")
print("=" * 50)

import os
import glob

# List cached files
cache_files = glob.glob("*.csv")
print("Cached data files:")
for file in cache_files:
    size = os.path.getsize(file) / 1024  # KB
    print(f"  {file}: {size:.1f} KB")

# Function to clear cache
def clear_cache():
    """Clear all cached CSV files."""
    for file in cache_files:
        os.remove(file)
        print(f"Removed: {file}")

# Uncomment to clear cache
# clear_cache()
```

## Real-time Applications

### WebSocket Integration

Real-time sports data streaming:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
from typing import List, Dict
from datetime import datetime

app = FastAPI()

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sport_subscribers: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, sport: str = None):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if sport:
            if sport not in self.sport_subscribers:
                self.sport_subscribers[sport] = []
            self.sport_subscribers[sport].append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
        
        # Remove from sport-specific subscriptions
        for sport, connections in self.sport_subscribers.items():
            if websocket in connections:
                connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client."""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Handle disconnected clients
                pass
    
    async def broadcast_to_sport(self, message: str, sport: str):
        """Broadcast message to sport-specific subscribers."""
        if sport in self.sport_subscribers:
            for connection in self.sport_subscribers[sport]:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

class SportsDataStreamer:
    """Stream real-time sports data updates."""
    
    def __init__(self, client: BallDontLieClient):
        self.client = client
        self.running = False
    
    async def start_streaming(self):
        """Start the data streaming process."""
        self.running = True
        
        while self.running:
            try:
                # Fetch latest data for each sport
                for sport in [Sport.NBA, Sport.NFL, Sport.MLB]:
                    # Get recent games (in progress or recently completed)
                    try:
                        games_response = await self.client.get_games(
                            sport, 
                            seasons=[2023],
                            per_page=10
                        )
                        
                        games = games_response.data['data']
                        live_games = [game for game in games if game['status'] in ['In Progress', 'Live']]
                        
                        if live_games:
                            update_message = {
                                'type': 'live_games',
                                'sport': sport.value,
                                'games': live_games,
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            
                            await manager.broadcast_to_sport(
                                json.dumps(update_message), 
                                sport.value
                            )
                    
                    except Exception as e:
                        print(f"Error streaming {sport.value} data: {e}")
                
                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                print(f"Streaming error: {e}")
                await asyncio.sleep(5)
    
    def stop_streaming(self):
        """Stop the streaming process."""
        self.running = False

# Initialize streamer
client = BallDontLieClient()
streamer = SportsDataStreamer(client)

@app.websocket("/ws/{sport}")
async def websocket_endpoint(websocket: WebSocket, sport: str):
    """WebSocket endpoint for sport-specific updates."""
    await manager.connect(websocket, sport)
    
    try:
        # Send initial data
        initial_response = await client.get_teams(Sport(sport))
        initial_message = {
            'type': 'initial_data',
            'sport': sport,
            'teams': initial_response.data['data'],
            'timestamp': datetime.utcnow().isoformat()
        }
        await manager.send_personal_message(json.dumps(initial_message), websocket)
        
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            # Handle client requests
            try:
                request = json.loads(data)
                if request.get('type') == 'get_players':
                    players_response = await client.get_players(
                        Sport(sport), 
                        search=request.get('search', '')
                    )
                    
                    response_message = {
                        'type': 'players_data',
                        'sport': sport,
                        'players': players_response.data['data'],
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(response_message), websocket)
            
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({'type': 'error', 'message': 'Invalid JSON'}),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """Start background streaming on app startup."""
    asyncio.create_task(streamer.start_streaming())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown."""
    streamer.stop_streaming()
    await client.close()

# Client-side JavaScript for WebSocket connection
websocket_client_html = """
<!DOCTYPE html>
<html>
<head>
    <title>HoopHead Real-time Sports Data</title>
</head>
<body>
    <h1>Real-time Sports Updates</h1>
    <div id="messages"></div>
    <input type="text" id="searchInput" placeholder="Search players...">
    <button onclick="searchPlayers()">Search</button>

    <script>
        const sport = 'nba';  // Change as needed
        const ws = new WebSocket(`ws://localhost:8000/ws/${sport}`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const messages = document.getElementById('messages');
            
            const messageElement = document.createElement('div');
            messageElement.innerHTML = `
                <h3>${data.type} - ${data.sport.toUpperCase()}</h3>
                <p>Time: ${new Date(data.timestamp).toLocaleString()}</p>
                <pre>${JSON.stringify(data, null, 2)}</pre>
                <hr>
            `;
            messages.insertBefore(messageElement, messages.firstChild);
        };
        
        function searchPlayers() {
            const search = document.getElementById('searchInput').value;
            ws.send(JSON.stringify({
                type: 'get_players',
                search: search
            }));
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(websocket_client_html)
```

### Redis Pub/Sub Integration

Advanced real-time data distribution:

```python
import redis.asyncio as redis
import json
from typing import Optional, Callable, Dict, Any

class SportsDataPublisher:
    """Publish sports data updates to Redis channels."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.client = BallDontLieClient()
    
    async def publish_team_update(self, sport: Sport, team_data: Dict[str, Any]):
        """Publish team data update."""
        channel = f"sports:{sport.value}:teams"
        message = {
            'type': 'team_update',
            'sport': sport.value,
            'data': team_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.redis_client.publish(channel, json.dumps(message))
    
    async def publish_game_update(self, sport: Sport, game_data: Dict[str, Any]):
        """Publish game data update."""
        channel = f"sports:{sport.value}:games"
        message = {
            'type': 'game_update',
            'sport': sport.value,
            'data': game_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.redis_client.publish(channel, json.dumps(message))
    
    async def start_monitoring(self):
        """Monitor for data changes and publish updates."""
        while True:
            try:
                # Check for live games and publish updates
                for sport in [Sport.NBA, Sport.NFL, Sport.MLB]:
                    games_response = await self.client.get_games(sport, per_page=50)
                    games = games_response.data['data']
                    
                    live_games = [game for game in games if game['status'] in ['In Progress', 'Live']]
                    
                    for game in live_games:
                        await self.publish_game_update(sport, game)
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(5)

class SportsDataSubscriber:
    """Subscribe to sports data updates from Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.handlers: Dict[str, Callable] = {}
    
    def register_handler(self, pattern: str, handler: Callable):
        """Register a handler for a channel pattern."""
        self.handlers[pattern] = handler
    
    async def subscribe_to_sport(self, sport: Sport):
        """Subscribe to all updates for a specific sport."""
        channels = [
            f"sports:{sport.value}:teams",
            f"sports:{sport.value}:games",
            f"sports:{sport.value}:players"
        ]
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(*channels)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    channel = message['channel'].decode('utf-8')
                    
                    # Find matching handler
                    for pattern, handler in self.handlers.items():
                        if pattern in channel:
                            await handler(data)
                            break
                
                except Exception as e:
                    print(f"Error processing message: {e}")

# Usage example
async def setup_realtime_sports():
    """Setup real-time sports data system."""
    
    # Publisher
    publisher = SportsDataPublisher()
    
    # Subscriber with handlers
    subscriber = SportsDataSubscriber()
    
    async def handle_game_update(data):
        print(f"Game update: {data['sport']} - {data['data']['status']}")
        # Process game update (send to WebSocket clients, update database, etc.)
    
    async def handle_team_update(data):
        print(f"Team update: {data['sport']} - {data['data']['name']}")
        # Process team update
    
    subscriber.register_handler('games', handle_game_update)
    subscriber.register_handler('teams', handle_team_update)
    
    # Start publisher and subscriber
    await asyncio.gather(
        publisher.start_monitoring(),
        subscriber.subscribe_to_sport(Sport.NBA),
        subscriber.subscribe_to_sport(Sport.NFL)
    )
```

## Batch Processing

### ETL Pipeline

Complete Extract, Transform, Load pipeline:

```python
import asyncio
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

@dataclass
class ETLConfig:
    """Configuration for ETL pipeline."""
    batch_size: int = 100
    parallel_workers: int = 5
    retry_attempts: int = 3
    output_format: str = 'parquet'  # 'csv', 'parquet', 'json'
    include_raw_data: bool = False
    sports: List[Sport] = None

class SportsDataETL:
    """Complete ETL pipeline for sports data."""
    
    def __init__(self, client: BallDontLieClient, config: ETLConfig):
        self.client = client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not config.sports:
            config.sports = [Sport.NBA, Sport.MLB, Sport.NFL, Sport.NHL, Sport.EPL]
    
    async def extract_teams(self, sport: Sport) -> List[Dict[str, Any]]:
        """Extract teams data for a sport."""
        try:
            response = await self.client.get_teams(sport)
            teams = response.data['data']
            
            # Add metadata
            for team in teams:
                team['_extracted_at'] = datetime.utcnow().isoformat()
                team['_sport'] = sport.value
                team['_source'] = 'ball_dont_lie_api'
            
            self.logger.info(f"Extracted {len(teams)} teams for {sport.value}")
            return teams
        
        except Exception as e:
            self.logger.error(f"Failed to extract teams for {sport.value}: {e}")
            return []
    
    async def extract_players(self, sport: Sport, max_pages: int = 50) -> List[Dict[str, Any]]:
        """Extract players data for a sport with pagination."""
        all_players = []
        page = 1
        
        while page <= max_pages:
            try:
                response = await self.client.get_players(
                    sport, 
                    page=page, 
                    per_page=self.config.batch_size
                )
                players = response.data['data']
                
                if not players:
                    break
                
                # Add metadata
                for player in players:
                    player['_extracted_at'] = datetime.utcnow().isoformat()
                    player['_sport'] = sport.value
                    player['_source'] = 'ball_dont_lie_api'
                    player['_page'] = page
                
                all_players.extend(players)
                page += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
                self.logger.info(f"Extracted page {page-1} for {sport.value} players ({len(players)} players)")
                
            except Exception as e:
                self.logger.error(f"Failed to extract players page {page} for {sport.value}: {e}")
                if self.config.retry_attempts > 0:
                    await asyncio.sleep(1)
                    continue
                else:
                    break
        
        self.logger.info(f"Total extracted {len(all_players)} players for {sport.value}")
        return all_players
    
    async def extract_games(self, sport: Sport, seasons: List[int] = None) -> List[Dict[str, Any]]:
        """Extract games data for specific seasons."""
        if not seasons:
            seasons = [2023]  # Default to current season
        
        all_games = []
        
        for season in seasons:
            page = 1
            while True:
                try:
                    response = await self.client.get_games(
                        sport,
                        seasons=[season],
                        page=page,
                        per_page=self.config.batch_size
                    )
                    games = response.data['data']
                    
                    if not games:
                        break
                    
                    # Add metadata
                    for game in games:
                        game['_extracted_at'] = datetime.utcnow().isoformat()
                        game['_sport'] = sport.value
                        game['_source'] = 'ball_dont_lie_api'
                        game['_season'] = season
                    
                    all_games.extend(games)
                    page += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Failed to extract games for {sport.value} season {season}: {e}")
                    break
        
        self.logger.info(f"Total extracted {len(all_games)} games for {sport.value}")
        return all_games
    
    def transform_teams(self, teams_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform teams data."""
        df = pd.DataFrame(teams_data)
        
        if df.empty:
            return df
        
        # Standardize column names
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        # Clean and standardize data
        if 'full_name' in df.columns:
            df['full_name'] = df['full_name'].str.strip()
        
        if 'city' in df.columns:
            df['city'] = df['city'].str.strip()
        
        if 'abbreviation' in df.columns:
            df['abbreviation'] = df['abbreviation'].str.upper()
        
        # Add computed columns
        df['team_key'] = df['_sport'] + '_' + df['abbreviation'].astype(str)
        df['extraction_date'] = pd.to_datetime(df['_extracted_at']).dt.date
        
        # Remove raw data if not needed
        if not self.config.include_raw_data:
            df = df.drop(columns=['_source'], errors='ignore')
        
        return df
    
    def transform_players(self, players_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform players data."""
        df = pd.DataFrame(players_data)
        
        if df.empty:
            return df
        
        # Flatten team data if present
        if 'team' in df.columns:
            team_df = pd.json_normalize(df['team'])
            team_df.columns = ['team_' + col for col in team_df.columns]
            df = pd.concat([df.drop('team', axis=1), team_df], axis=1)
        
        # Clean height and weight
        if 'height' in df.columns:
            df['height_inches'] = df['height'].apply(self._parse_height)
        
        if 'weight' in df.columns:
            df['weight_lbs'] = pd.to_numeric(df['weight'], errors='coerce')
        
        # Create full name
        if 'first_name' in df.columns and 'last_name' in df.columns:
            df['full_name'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
            df['full_name'] = df['full_name'].str.strip()
        
        # Player key
        df['player_key'] = df['_sport'] + '_' + df['id'].astype(str)
        
        return df
    
    def transform_games(self, games_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform games data."""
        df = pd.DataFrame(games_data)
        
        if df.empty:
            return df
        
        # Parse dates
        if 'date' in df.columns:
            df['game_date'] = pd.to_datetime(df['date'], errors='coerce')
        
        if 'datetime' in df.columns:
            df['game_datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        
        # Calculate score differentials
        if 'home_team_score' in df.columns and 'visitor_team_score' in df.columns:
            df['score_differential'] = df['home_team_score'] - df['visitor_team_score']
            df['total_score'] = df['home_team_score'] + df['visitor_team_score']
            df['home_win'] = df['home_team_score'] > df['visitor_team_score']
        
        # Game key
        df['game_key'] = df['_sport'] + '_' + df['id'].astype(str)
        
        return df
    
    def _parse_height(self, height_str) -> Optional[int]:
        """Parse height string to inches."""
        if pd.isna(height_str) or not height_str:
            return None
        
        try:
            if '-' in str(height_str):
                feet, inches = str(height_str).split('-')
                return int(feet) * 12 + int(inches)
        except:
            pass
        return None
    
    async def load_data(self, df: pd.DataFrame, entity_type: str, sport: Sport):
        """Load transformed data to storage."""
        if df.empty:
            self.logger.warning(f"No data to load for {sport.value} {entity_type}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{sport.value}_{entity_type}_{timestamp}"
        
        if self.config.output_format == 'parquet':
            output_file = f"{filename}.parquet"
            df.to_parquet(output_file, index=False)
        elif self.config.output_format == 'csv':
            output_file = f"{filename}.csv"
            df.to_csv(output_file, index=False)
        elif self.config.output_format == 'json':
            output_file = f"{filename}.json"
            df.to_json(output_file, orient='records', indent=2)
        
        self.logger.info(f"Loaded {len(df)} records to {output_file}")
    
    async def run_etl_pipeline(self, entity_types: List[str] = None):
        """Run complete ETL pipeline."""
        if not entity_types:
            entity_types = ['teams', 'players', 'games']
        
        for sport in self.config.sports:
            self.logger.info(f"Starting ETL for {sport.value}")
            
            if 'teams' in entity_types:
                # Extract, Transform, Load teams
                teams_data = await self.extract_teams(sport)
                teams_df = self.transform_teams(teams_data)
                await self.load_data(teams_df, 'teams', sport)
            
            if 'players' in entity_types:
                # Extract, Transform, Load players
                players_data = await self.extract_players(sport)
                players_df = self.transform_players(players_data)
                await self.load_data(players_df, 'players', sport)
            
            if 'games' in entity_types:
                # Extract, Transform, Load games
                games_data = await self.extract_games(sport)
                games_df = self.transform_games(games_data)
                await self.load_data(games_df, 'games', sport)
            
            self.logger.info(f"Completed ETL for {sport.value}")

# Usage
async def run_daily_etl():
    """Run daily ETL pipeline."""
    client = BallDontLieClient()
    
    config = ETLConfig(
        batch_size=100,
        parallel_workers=3,
        output_format='parquet',
        include_raw_data=False,
        sports=[Sport.NBA, Sport.NFL, Sport.MLB]
    )
    
    etl = SportsDataETL(client, config)
    
    # Run ETL for all entity types
    await etl.run_etl_pipeline(['teams', 'players', 'games'])
    
    await client.close()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run ETL
    asyncio.run(run_daily_etl())
```

---

## Next Steps

- Review [Error Handling Guide](ERROR_HANDLING.md) for robust error management
- Check [Extension Guide](EXTENSION_GUIDE.md) for adding custom functionality
- See [Performance Optimization Guide](PERFORMANCE.md) for scaling best practices

For technical support, refer to the main [HoopHead Documentation](../README.md). 