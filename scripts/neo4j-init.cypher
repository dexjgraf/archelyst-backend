// Neo4j Initialization Script for Archelyst Financial Platform
// Creates sample nodes and relationships for financial data

// Create constraints and indexes
CREATE CONSTRAINT company_symbol IF NOT EXISTS FOR (c:Company) REQUIRE c.symbol IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT portfolio_id IF NOT EXISTS FOR (p:Portfolio) REQUIRE p.portfolio_id IS UNIQUE;

CREATE INDEX sector_name IF NOT EXISTS FOR (s:Sector) ON (s.name);
CREATE INDEX industry_name IF NOT EXISTS FOR (i:Industry) ON (i.name);

// Create Sectors
CREATE (tech:Sector {name: "Technology", description: "Technology companies"})
CREATE (finance:Sector {name: "Financial Services", description: "Banks and financial institutions"})
CREATE (healthcare:Sector {name: "Healthcare", description: "Healthcare and pharmaceutical companies"})
CREATE (energy:Sector {name: "Energy", description: "Oil, gas, and renewable energy companies"});

// Create Industries
CREATE (software:Industry {name: "Software", description: "Software development companies"})
CREATE (semiconductors:Industry {name: "Semiconductors", description: "Chip and semiconductor manufacturers"})
CREATE (banking:Industry {name: "Banking", description: "Commercial and investment banks"})
CREATE (biotech:Industry {name: "Biotechnology", description: "Biotechnology and pharmaceutical research"});

// Create Companies
CREATE (aapl:Company {
  symbol: "AAPL",
  name: "Apple Inc.",
  market_cap: 3000000000000,
  employees: 164000,
  founded: 1976,
  headquarters: "Cupertino, CA",
  website: "https://www.apple.com",
  description: "Technology company specializing in consumer electronics"
})
CREATE (msft:Company {
  symbol: "MSFT", 
  name: "Microsoft Corporation",
  market_cap: 2800000000000,
  employees: 221000,
  founded: 1975,
  headquarters: "Redmond, WA",
  website: "https://www.microsoft.com",
  description: "Technology company developing software and cloud services"
})
CREATE (googl:Company {
  symbol: "GOOGL",
  name: "Alphabet Inc.",
  market_cap: 1700000000000,
  employees: 182000,
  founded: 1998,
  headquarters: "Mountain View, CA", 
  website: "https://www.alphabet.com",
  description: "Technology conglomerate specializing in internet services"
})
CREATE (tsla:Company {
  symbol: "TSLA",
  name: "Tesla Inc.",
  market_cap: 800000000000,
  employees: 140000,
  founded: 2003,
  headquarters: "Austin, TX",
  website: "https://www.tesla.com",
  description: "Electric vehicle and clean energy company"
})
CREATE (jpm:Company {
  symbol: "JPM",
  name: "JPMorgan Chase & Co.",
  market_cap: 500000000000,
  employees: 288000,
  founded: 1799,
  headquarters: "New York, NY",
  website: "https://www.jpmorganchase.com",
  description: "Multinational investment bank and financial services company"
});

// Create sample Users
CREATE (user1:User {
  user_id: "user_001",
  email: "investor1@example.com",
  username: "tech_investor",
  role: "premium",
  created_at: datetime(),
  risk_tolerance: "moderate"
})
CREATE (user2:User {
  user_id: "user_002", 
  email: "trader@example.com",
  username: "day_trader",
  role: "user",
  created_at: datetime(),
  risk_tolerance: "high"
});

// Create Portfolios
CREATE (portfolio1:Portfolio {
  portfolio_id: "port_001",
  name: "Tech Growth Portfolio",
  created_at: datetime(),
  total_value: 150000,
  strategy: "growth"
})
CREATE (portfolio2:Portfolio {
  portfolio_id: "port_002",
  name: "Diversified Portfolio", 
  created_at: datetime(),
  total_value: 75000,
  strategy: "balanced"
});

// Create Holdings
CREATE (holding1:Holding {
  shares: 100,
  avg_cost: 150.00,
  current_price: 175.00,
  purchase_date: date("2024-01-15"),
  portfolio_weight: 0.35
})
CREATE (holding2:Holding {
  shares: 50,
  avg_cost: 280.00, 
  current_price: 320.00,
  purchase_date: date("2024-02-01"),
  portfolio_weight: 0.40
});

// Create relationships
MATCH (tech:Sector {name: "Technology"})
MATCH (software:Industry {name: "Software"})
MATCH (semiconductors:Industry {name: "Semiconductors"})
MATCH (aapl:Company {symbol: "AAPL"})
MATCH (msft:Company {symbol: "MSFT"})
MATCH (googl:Company {symbol: "GOOGL"})
MATCH (tsla:Company {symbol: "TSLA"})

CREATE (tech)-[:CONTAINS]->(software)
CREATE (tech)-[:CONTAINS]->(semiconductors)
CREATE (aapl)-[:BELONGS_TO]->(tech)
CREATE (msft)-[:BELONGS_TO]->(tech)
CREATE (googl)-[:BELONGS_TO]->(tech)
CREATE (tsla)-[:BELONGS_TO]->(tech)
CREATE (aapl)-[:OPERATES_IN]->(software)
CREATE (msft)-[:OPERATES_IN]->(software);

MATCH (finance:Sector {name: "Financial Services"})
MATCH (banking:Industry {name: "Banking"})
MATCH (jpm:Company {symbol: "JPM"})

CREATE (finance)-[:CONTAINS]->(banking)
CREATE (jpm)-[:BELONGS_TO]->(finance)
CREATE (jpm)-[:OPERATES_IN]->(banking);

// User-Portfolio relationships
MATCH (user1:User {user_id: "user_001"})
MATCH (user2:User {user_id: "user_002"})
MATCH (portfolio1:Portfolio {portfolio_id: "port_001"})
MATCH (portfolio2:Portfolio {portfolio_id: "port_002"})

CREATE (user1)-[:OWNS]->(portfolio1)
CREATE (user2)-[:OWNS]->(portfolio2);

// Portfolio-Company holdings
MATCH (portfolio1:Portfolio {portfolio_id: "port_001"})
MATCH (portfolio2:Portfolio {portfolio_id: "port_002"})
MATCH (aapl:Company {symbol: "AAPL"})
MATCH (msft:Company {symbol: "MSFT"})
MATCH (holding1:Holding)
MATCH (holding2:Holding)

CREATE (portfolio1)-[:HOLDS]->(holding1)-[:OF_COMPANY]->(aapl)
CREATE (portfolio2)-[:HOLDS]->(holding2)-[:OF_COMPANY]->(msft);

// Company correlations (example financial relationships)
MATCH (aapl:Company {symbol: "AAPL"})
MATCH (msft:Company {symbol: "MSFT"})
MATCH (googl:Company {symbol: "GOOGL"})

CREATE (aapl)-[:CORRELATED_WITH {correlation: 0.75, period: "1Y"}]->(msft)
CREATE (msft)-[:CORRELATED_WITH {correlation: 0.68, period: "1Y"}]->(googl)
CREATE (aapl)-[:COMPETES_WITH {market: "consumer_electronics"}]->(googl);

// Create some market events
CREATE (event1:MarketEvent {
  event_id: "event_001",
  name: "Fed Interest Rate Decision",
  date: date("2024-03-20"),
  type: "monetary_policy",
  impact: "market_wide",
  description: "Federal Reserve announces interest rate decision"
})
CREATE (event2:MarketEvent {
  event_id: "event_002", 
  name: "Apple Earnings Report",
  date: date("2024-01-25"),
  type: "earnings",
  impact: "company_specific",
  description: "Apple Q1 2024 earnings announcement"
});

// Link events to companies
MATCH (event1:MarketEvent {event_id: "event_001"})
MATCH (event2:MarketEvent {event_id: "event_002"})
MATCH (aapl:Company {symbol: "AAPL"})
MATCH (msft:Company {symbol: "MSFT"})
MATCH (jpm:Company {symbol: "JPM"})

CREATE (event1)-[:AFFECTS {impact_score: 0.8}]->(jpm)
CREATE (event1)-[:AFFECTS {impact_score: 0.6}]->(aapl)
CREATE (event2)-[:DIRECTLY_AFFECTS {impact_score: 0.95}]->(aapl);

RETURN "Neo4j initialization completed successfully!" as message;