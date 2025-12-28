#!/bin/bash
# ===========================================
# Flask Grade Tracker - Docker Build & Deploy Script
# ===========================================

set -e  # Exit on error

echo "🚀 Starting Grade Tracker containerization..."

# ===========================================
# STEP 1: Environment Setup
# ===========================================
echo "📋 Setting up environment..."

if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env file with your configuration before proceeding!"
    exit 1
fi

# ===========================================
# STEP 2: Build Application
# ===========================================
echo "🔨 Building Docker images with UV (fast Python package manager)..."

# Build the main application image
docker-compose build web

echo "✅ Docker images built successfully!"

# ===========================================
# STEP 3: Start Services
# ===========================================
echo "🚀 Starting services..."

# Start database and Redis first
docker-compose up -d mysql redis

# Wait for database to be ready
echo "⏳ Waiting for MySQL to be ready..."
while ! docker-compose exec mysql mysqladmin ping -h localhost --silent; do
    sleep 2
done

echo "✅ MySQL is ready!"

# ===========================================
# STEP 4: Database Initialization
# ===========================================
echo "📊 Setting up database..."

# Initialize database tables (this app uses db.create_all() not flask-migrate)
echo "🔧 Creating database tables..."
docker-compose run --rm web python -c "
from app import create_app
from app.models import db
app = create_app('production')
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"

echo "✅ Database initialization completed!"

# ===========================================
# STEP 5: Start All Services
# ===========================================
echo "🌐 Starting all services..."

# Start the web application and background workers
docker-compose up -d

# ===========================================
# STEP 6: Health Check
# ===========================================
echo "🏥 Performing health checks..."

sleep 10  # Give services time to start

# Check if web service is healthy
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Web service is healthy!"
else
    echo "❌ Web service health check failed!"
    echo "📋 Checking logs..."
    docker-compose logs web
fi

# ===========================================
# STEP 7: Summary
# ===========================================
echo ""
echo "🎉 Grade Tracker deployment complete!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 Application URLs:"
echo "   • Main App: http://localhost:5000"
echo "   • MySQL:    localhost:3306"
echo "   • Redis:    localhost:6379"
echo ""
echo "📋 Useful Commands:"
echo "   • View logs:     docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Rebuild:       docker-compose build"
echo "   • Shell access:  docker-compose exec web bash"
echo ""
echo "✅ Setup complete! Your Grade Tracker is now running in containers."