#!/bin/bash
# =============================================================================
# KVPL Database Setup Script (Bash)
# One-command PostgreSQL database initialization
# 
# Usage: 
#   chmod +x setup_db.sh
#   ./setup_db.sh [database_name] [username] [password]
#
# Default Values:
#   database_name: kvpl
#   username: kvpl_user
#   password: (prompted)
# =============================================================================

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DB_NAME="${1:-kvpl}"
DB_USER="${2:-kvpl_user}"
DB_PASSWORD="${3:-}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  KVPL Database Setup Script                                   ║${NC}"
echo -e "${BLUE}║  PostgreSQL Configuration & Initialization                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not installed or not in PATH${NC}"
    echo "Please install PostgreSQL 12 or higher"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL found${NC}"
psql --version

# Prompt for password if not provided
if [ -z "$DB_PASSWORD" ]; then
    echo -e "\n${YELLOW}Enter password for PostgreSQL user '${DB_USER}':${NC}"
    read -s DB_PASSWORD
    echo ""
fi

# Create .env file
echo -e "\n${BLUE}Creating .env file...${NC}"
cat > .env << EOF
# KVPL Database Configuration
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=${DB_NAME}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_SECRET_KEY=$(openssl rand -hex 32)

# Application
APP_HOST=0.0.0.0
APP_PORT=5000
EOF
echo -e "${GREEN}✓ .env file created${NC}"

# Connect to PostgreSQL and create database
echo -e "\n${BLUE}Setting up PostgreSQL database...${NC}"

# Check if running as root/with sudo
PSQL_CMD="psql"
if [ "$EUID" -eq 0 ]; then
    PSQL_CMD="psql -U postgres"
fi

# Create database and user
$PSQL_CMD << POSTGRES_SCRIPT
-- Create user if not exists
CREATE USER "$DB_USER" WITH PASSWORD '$DB_PASSWORD' CREATEDB;

-- Create database if not exists
CREATE DATABASE "$DB_NAME" OWNER "$DB_USER";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL PRIVILEGES ON SCHEMA public TO "$DB_USER";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$DB_USER";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$DB_USER";

-- Allow future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "$DB_USER";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "$DB_USER";

-- Verify
SELECT current_user;
POSTGRES_SCRIPT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create database${NC}"
    exit 1
fi

# Test connection
echo -e "\n${BLUE}Testing database connection...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -h localhost -c "SELECT 'Connection successful' AS status;" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Install Python requirements if pip is available
if command -v pip &> /dev/null; then
    echo -e "\n${BLUE}Installing Python dependencies...${NC}"
    pip install -q -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠ Could not install dependencies${NC}"
    fi
fi

# Run migrations if Python is available
if command -v python3 &> /dev/null; then
    echo -e "\n${BLUE}Running database migrations...${NC}"
    python3 migrate.py migrate
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${RED}❌ Migration failed${NC}"
        exit 1
    fi
fi

# Summary
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Connection Details:${NC}"
echo -e "  Database: ${GREEN}${DB_NAME}${NC}"
echo -e "  User: ${GREEN}${DB_USER}${NC}"
echo -e "  Host: ${GREEN}localhost${NC}"
echo -e "  Port: ${GREEN}5432${NC}"

echo -e "\n${BLUE}Environment:${NC}"
echo -e "  .env file created at: ${GREEN}$(pwd)/.env${NC}"

echo -e "\n${BLUE}Connect via psql:${NC}"
echo -e "  ${GREEN}psql -U ${DB_USER} -d ${DB_NAME}${NC}"

echo -e "\n${BLUE}Connect in Python:${NC}"
echo -e "  ${GREEN}DATABASE_URL=postgresql://${DB_USER}:****@localhost:5432/${DB_NAME}${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "  1. Review configuration: ${GREEN}cat .env${NC}"
echo -e "  2. Start Flask app: ${GREEN}python3 app.py${NC}"
echo -e "  3. Check migration status: ${GREEN}python3 migrate.py status${NC}"
echo -e "  4. See queries: ${GREEN}cat migrations/QUERIES.sql${NC}"

echo -e "\n${BLUE}Documentation:${NC}"
echo -e "  Setup guide: ${GREEN}GETTING_STARTED.md${NC}"
echo -e "  Migration docs: ${GREEN}migrations/README.md${NC}"
echo -e "  SQL queries: ${GREEN}migrations/QUERIES.sql${NC}\n"
