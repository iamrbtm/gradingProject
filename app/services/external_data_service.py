"""
Advanced External Data Integration Service
=========================================

This service integrates multiple external data sources to enhance ML predictions:
- Academic calendars and institutional data
- Weather data (affects student performance)
- Economic indicators (affects student stress/performance)
- Social media sentiment (general mood indicators)
- Course difficulty metrics from external sources
- Industry job market data (motivation factors)
- Campus event data (affects study patterns)

Author: Advanced ML Team
Date: 2024-12-20
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import requests
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import aiohttp
import json
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from app.models import db, User, Course, Term, Assignment
from app.logging_config import get_logger

logger = get_logger(__name__)


class DataSourceType(Enum):
    """Types of external data sources."""

    WEATHER = "weather"
    ACADEMIC_CALENDAR = "academic_calendar"
    ECONOMIC = "economic"
    SOCIAL_SENTIMENT = "social_sentiment"
    COURSE_DIFFICULTY = "course_difficulty"
    JOB_MARKET = "job_market"
    CAMPUS_EVENTS = "campus_events"
    INDUSTRY_TRENDS = "industry_trends"


@dataclass
class ExternalDataPoint:
    """Represents a single external data point."""

    source_type: DataSourceType
    timestamp: datetime
    value: float
    metadata: Dict[str, Any]
    confidence: float
    freshness_score: float


@dataclass
class WeatherData:
    """Weather data structure."""

    temperature: float
    humidity: float
    pressure: float
    precipitation: float
    wind_speed: float
    cloud_cover: float
    uv_index: float
    weather_condition: str
    timestamp: datetime


@dataclass
class EconomicIndicators:
    """Economic indicators structure."""

    unemployment_rate: float
    inflation_rate: float
    stock_market_index: float
    consumer_confidence: float
    gas_prices: float
    housing_costs: float
    timestamp: datetime


@dataclass
class CourseDifficultyMetrics:
    """Course difficulty metrics from external sources."""

    average_grade: float
    drop_rate: float
    pass_rate: float
    time_investment_hours: float
    prerequisite_success_rate: float
    instructor_rating: float
    course_load_index: float


class ExternalDataIntegrationService:
    """
    Advanced service for integrating multiple external data sources
    to enhance ML predictions with real-world context.
    """

    def __init__(self):
        self.data_sources = {}
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        self.executor = ThreadPoolExecutor(max_workers=10)

        # API keys and endpoints (would be in environment variables)
        self.api_keys = {
            "weather": "demo_weather_key",
            "economic": "demo_economic_key",
            "sentiment": "demo_sentiment_key",
            "academic": "demo_academic_key",
        }

        self.endpoints = {
            "weather": "https://api.openweathermap.org/data/2.5",
            "economic": "https://api.stlouisfed.org/fred/series",
            "sentiment": "https://api.twitter.com/2/tweets",
            "academic": "https://api.example-university.edu",
        }

    async def get_comprehensive_external_data(
        self, user_id: int, course_id: Optional[int] = None, lookback_days: int = 30
    ) -> Dict[str, List[ExternalDataPoint]]:
        """
        Get comprehensive external data for enhanced ML predictions.

        Args:
            user_id: User ID for personalized data
            course_id: Optional course ID for course-specific data
            lookback_days: Number of days to look back for historical data

        Returns:
            Dictionary of external data points organized by source type
        """
        try:
            logger.info(
                f"Gathering external data for user {user_id}, course {course_id}"
            )

            # Get user location and preferences for personalized data
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Parallel data collection from multiple sources
            tasks = []

            # Weather data (affects cognitive performance)
            tasks.append(
                self._get_weather_data(
                    user.location if hasattr(user, "location") else "Default"
                )
            )

            # Economic indicators (affects student stress and motivation)
            tasks.append(self._get_economic_indicators())

            # Academic calendar events (affects study patterns)
            tasks.append(self._get_academic_calendar_data(user_id))

            # Social sentiment data (general mood indicators)
            tasks.append(self._get_social_sentiment_data())

            # Course-specific data if course provided
            if course_id:
                tasks.append(self._get_course_difficulty_data(course_id))
                tasks.append(self._get_industry_trends_data(course_id))

            # Campus events data
            tasks.append(self._get_campus_events_data(user_id))

            # Job market data (affects motivation)
            tasks.append(self._get_job_market_data(user_id, course_id))

            # Execute all data collection tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process and organize results
            external_data = {}
            source_types = [
                DataSourceType.WEATHER,
                DataSourceType.ECONOMIC,
                DataSourceType.ACADEMIC_CALENDAR,
                DataSourceType.SOCIAL_SENTIMENT,
            ]

            if course_id:
                source_types.extend(
                    [DataSourceType.COURSE_DIFFICULTY, DataSourceType.INDUSTRY_TRENDS]
                )

            source_types.extend(
                [DataSourceType.CAMPUS_EVENTS, DataSourceType.JOB_MARKET]
            )

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        f"Failed to collect data from source {source_types[i]}: {result}"
                    )
                    external_data[source_types[i].value] = []
                else:
                    external_data[source_types[i].value] = result

            logger.info(
                f"Successfully collected external data from {len(external_data)} sources"
            )
            return external_data

        except Exception as e:
            logger.error(f"Error collecting external data: {str(e)}")
            return {}

    async def _get_weather_data(
        self, location: str = "Default"
    ) -> List[ExternalDataPoint]:
        """Get weather data that correlates with cognitive performance."""
        try:
            # Simulated weather data - in production, use real weather API
            weather_data = [
                WeatherData(
                    temperature=72.5,
                    humidity=0.45,
                    pressure=1013.2,
                    precipitation=0.0,
                    wind_speed=5.2,
                    cloud_cover=0.2,
                    uv_index=6.0,
                    weather_condition="clear",
                    timestamp=datetime.utcnow() - timedelta(hours=i),
                )
                for i in range(24)  # Last 24 hours
            ]

            # Convert to ExternalDataPoint format
            data_points = []
            for weather in weather_data:
                # Weather comfort index (affects cognitive performance)
                comfort_index = self._calculate_weather_comfort_index(weather)

                data_points.append(
                    ExternalDataPoint(
                        source_type=DataSourceType.WEATHER,
                        timestamp=weather.timestamp,
                        value=comfort_index,
                        metadata={
                            "temperature": weather.temperature,
                            "humidity": weather.humidity,
                            "condition": weather.weather_condition,
                            "uv_index": weather.uv_index,
                        },
                        confidence=0.85,
                        freshness_score=1.0,
                    )
                )

            return data_points

        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            return []

    def _calculate_weather_comfort_index(self, weather: WeatherData) -> float:
        """
        Calculate weather comfort index that correlates with cognitive performance.

        Research shows optimal conditions for learning:
        - Temperature: 68-72°F (20-22°C)
        - Humidity: 40-60%
        - Low precipitation
        - Moderate UV (not too high/low)
        """
        # Temperature comfort (optimal around 70°F)
        temp_comfort = 1.0 - abs(weather.temperature - 70) / 30
        temp_comfort = max(0, min(1, temp_comfort))

        # Humidity comfort (optimal 40-60%)
        if 0.4 <= weather.humidity <= 0.6:
            humidity_comfort = 1.0
        elif weather.humidity < 0.4:
            humidity_comfort = weather.humidity / 0.4
        else:
            humidity_comfort = (1.0 - weather.humidity) / 0.4

        # Precipitation impact (negative)
        precip_comfort = max(0, 1.0 - weather.precipitation / 10)

        # UV comfort (moderate is best)
        uv_comfort = 1.0 - abs(weather.uv_index - 5) / 10
        uv_comfort = max(0, min(1, uv_comfort))

        # Combined comfort index (0-1 scale)
        comfort_index = (
            temp_comfort * 0.4
            + humidity_comfort * 0.3
            + precip_comfort * 0.2
            + uv_comfort * 0.1
        )

        return comfort_index

    async def _get_economic_indicators(self) -> List[ExternalDataPoint]:
        """Get economic indicators that affect student stress and motivation."""
        try:
            # Simulated economic data - in production, use FRED API or similar
            economic_data = [
                EconomicIndicators(
                    unemployment_rate=4.2,
                    inflation_rate=3.1,
                    stock_market_index=4500.0,
                    consumer_confidence=98.5,
                    gas_prices=3.45,
                    housing_costs=2800.0,
                    timestamp=datetime.utcnow() - timedelta(days=i),
                )
                for i in range(30)  # Last 30 days
            ]

            data_points = []
            for econ in economic_data:
                # Economic stress index (higher = more stress)
                stress_index = self._calculate_economic_stress_index(econ)

                data_points.append(
                    ExternalDataPoint(
                        source_type=DataSourceType.ECONOMIC,
                        timestamp=econ.timestamp,
                        value=1.0 - stress_index,  # Invert so higher = better
                        metadata={
                            "unemployment_rate": econ.unemployment_rate,
                            "inflation_rate": econ.inflation_rate,
                            "consumer_confidence": econ.consumer_confidence,
                            "gas_prices": econ.gas_prices,
                        },
                        confidence=0.75,
                        freshness_score=0.9,
                    )
                )

            return data_points

        except Exception as e:
            logger.error(f"Error getting economic data: {str(e)}")
            return []

    def _calculate_economic_stress_index(self, econ: EconomicIndicators) -> float:
        """Calculate economic stress index that affects student performance."""
        # Normalize indicators (0-1 scale, 1 = high stress)

        # Unemployment stress (higher unemployment = more stress)
        unemployment_stress = min(1.0, econ.unemployment_rate / 10.0)

        # Inflation stress (higher inflation = more stress)
        inflation_stress = min(1.0, econ.inflation_rate / 8.0)

        # Consumer confidence (higher confidence = less stress)
        confidence_stress = max(0, (120 - econ.consumer_confidence) / 120)

        # Gas prices stress (higher prices = more stress)
        gas_stress = min(1.0, max(0, (econ.gas_prices - 2.0) / 3.0))

        # Combined stress index
        stress_index = (
            unemployment_stress * 0.3
            + inflation_stress * 0.25
            + confidence_stress * 0.25
            + gas_stress * 0.2
        )

        return stress_index

    async def _get_academic_calendar_data(
        self, user_id: int
    ) -> List[ExternalDataPoint]:
        """Get academic calendar events that affect study patterns."""
        try:
            # Simulated academic calendar data
            events = [
                {
                    "event": "midterm_week",
                    "date": datetime.utcnow() + timedelta(days=7),
                    "stress_factor": 0.8,
                    "duration_days": 5,
                },
                {
                    "event": "spring_break",
                    "date": datetime.utcnow() + timedelta(days=21),
                    "stress_factor": -0.3,  # Negative = relaxing
                    "duration_days": 7,
                },
                {
                    "event": "finals_week",
                    "date": datetime.utcnow() + timedelta(days=45),
                    "stress_factor": 1.0,
                    "duration_days": 5,
                },
            ]

            data_points = []
            current_date = datetime.utcnow()

            # Generate stress level predictions for next 60 days
            for i in range(60):
                date = current_date + timedelta(days=i)
                stress_level = 0.0

                # Calculate stress from upcoming events
                for event in events:
                    days_until = (event["date"] - date).days
                    if (
                        -event["duration_days"] <= days_until <= 14
                    ):  # Event influence range
                        # Stress increases as event approaches, peaks during event
                        if days_until > 0:
                            influence = event["stress_factor"] * (1 - days_until / 14)
                        else:
                            influence = event["stress_factor"]  # During event
                        stress_level += influence

                # Normalize stress level
                stress_level = max(-1.0, min(1.0, stress_level))

                data_points.append(
                    ExternalDataPoint(
                        source_type=DataSourceType.ACADEMIC_CALENDAR,
                        timestamp=date,
                        value=1.0 - ((stress_level + 1) / 2),  # Convert to 0-1 scale
                        metadata={
                            "stress_level": stress_level,
                            "upcoming_events": len(events),
                        },
                        confidence=0.9,
                        freshness_score=1.0,
                    )
                )

            return data_points

        except Exception as e:
            logger.error(f"Error getting academic calendar data: {str(e)}")
            return []

    async def _get_social_sentiment_data(self) -> List[ExternalDataPoint]:
        """Get social sentiment data as general mood indicator."""
        try:
            # Simulated social sentiment data
            # In production, could use Twitter API, Reddit API, etc.
            sentiment_scores = []

            for i in range(7):  # Last 7 days
                date = datetime.utcnow() - timedelta(days=i)

                # Simulate daily sentiment with some trend
                base_sentiment = 0.6 + 0.2 * np.sin(i * 0.5)  # Cyclical pattern
                noise = np.random.normal(0, 0.1)
                sentiment = max(0, min(1, base_sentiment + noise))

                sentiment_scores.append(
                    ExternalDataPoint(
                        source_type=DataSourceType.SOCIAL_SENTIMENT,
                        timestamp=date,
                        value=sentiment,
                        metadata={
                            "source": "aggregated_social_media",
                            "sample_size": 10000 + i * 500,
                        },
                        confidence=0.65,
                        freshness_score=1.0 - (i * 0.1),
                    )
                )

            return sentiment_scores

        except Exception as e:
            logger.error(f"Error getting social sentiment data: {str(e)}")
            return []

    async def _get_course_difficulty_data(
        self, course_id: int
    ) -> List[ExternalDataPoint]:
        """Get course difficulty metrics from external sources."""
        try:
            course = Course.query.get(course_id)
            if not course:
                return []

            # Simulated course difficulty data
            # In production, could integrate with Rate My Professor,
            # university databases, etc.

            difficulty_metrics = CourseDifficultyMetrics(
                average_grade=82.5,  # Average grade in similar courses
                drop_rate=0.15,  # 15% drop rate
                pass_rate=0.89,  # 89% pass rate
                time_investment_hours=12.5,  # Hours per week
                prerequisite_success_rate=0.85,
                instructor_rating=4.2,
                course_load_index=0.7,  # 0-1 scale
            )

            # Convert metrics to performance prediction factor
            difficulty_factor = self._calculate_course_difficulty_factor(
                difficulty_metrics
            )

            data_point = ExternalDataPoint(
                source_type=DataSourceType.COURSE_DIFFICULTY,
                timestamp=datetime.utcnow(),
                value=difficulty_factor,
                metadata={
                    "average_grade": difficulty_metrics.average_grade,
                    "drop_rate": difficulty_metrics.drop_rate,
                    "time_investment": difficulty_metrics.time_investment_hours,
                    "instructor_rating": difficulty_metrics.instructor_rating,
                },
                confidence=0.8,
                freshness_score=0.7,  # Static data, lower freshness
            )

            return [data_point]

        except Exception as e:
            logger.error(f"Error getting course difficulty data: {str(e)}")
            return []

    def _calculate_course_difficulty_factor(
        self, metrics: CourseDifficultyMetrics
    ) -> float:
        """Calculate overall course difficulty factor."""
        # Higher average grade = easier course
        grade_factor = metrics.average_grade / 100.0

        # Lower drop rate = easier course
        drop_factor = 1.0 - metrics.drop_rate

        # Higher pass rate = easier course
        pass_factor = metrics.pass_rate

        # Lower time investment = easier course
        time_factor = max(0, 1.0 - (metrics.time_investment_hours - 8) / 20)

        # Higher instructor rating = better experience
        instructor_factor = metrics.instructor_rating / 5.0

        # Combined difficulty factor (0-1, higher = easier/better)
        difficulty_factor = (
            grade_factor * 0.3
            + drop_factor * 0.25
            + pass_factor * 0.2
            + time_factor * 0.15
            + instructor_factor * 0.1
        )

        return difficulty_factor

    async def _get_campus_events_data(self, user_id: int) -> List[ExternalDataPoint]:
        """Get campus events that might affect study patterns."""
        try:
            # Simulated campus events
            events = [
                {
                    "name": "Career Fair",
                    "date": datetime.utcnow() + timedelta(days=3),
                    "impact": 0.2,  # Positive impact on motivation
                    "duration": 1,
                },
                {
                    "name": "Football Game",
                    "date": datetime.utcnow() + timedelta(days=5),
                    "impact": -0.1,  # Slight negative on study focus
                    "duration": 1,
                },
                {
                    "name": "Study Week",
                    "date": datetime.utcnow() + timedelta(days=14),
                    "impact": 0.3,  # Positive study environment
                    "duration": 7,
                },
            ]

            data_points = []
            for i in range(30):  # Next 30 days
                date = datetime.utcnow() + timedelta(days=i)
                event_impact = 0.0

                # Calculate cumulative event impact
                for event in events:
                    days_diff = abs((event["date"] - date).days)
                    if days_diff <= event["duration"]:
                        event_impact += event["impact"]
                    elif days_diff <= 3:  # Pre-event influence
                        event_impact += event["impact"] * 0.5

                # Base level + event impact
                campus_factor = 0.5 + event_impact
                campus_factor = max(0, min(1, campus_factor))

                data_points.append(
                    ExternalDataPoint(
                        source_type=DataSourceType.CAMPUS_EVENTS,
                        timestamp=date,
                        value=campus_factor,
                        metadata={"active_events": len(events)},
                        confidence=0.7,
                        freshness_score=0.8,
                    )
                )

            return data_points

        except Exception as e:
            logger.error(f"Error getting campus events data: {str(e)}")
            return []

    async def _get_job_market_data(
        self, user_id: int, course_id: Optional[int] = None
    ) -> List[ExternalDataPoint]:
        """Get job market data that affects student motivation."""
        try:
            # Simulated job market data
            # In production, integrate with LinkedIn, Indeed, Bureau of Labor Statistics

            if course_id:
                course = Course.query.get(course_id)
                field = getattr(course, "field", "General")
            else:
                field = "General"

            # Market conditions by field
            market_conditions = {
                "Computer Science": {
                    "growth_rate": 0.22,
                    "avg_salary": 95000,
                    "job_openings": 50000,
                },
                "Engineering": {
                    "growth_rate": 0.08,
                    "avg_salary": 80000,
                    "job_openings": 25000,
                },
                "Business": {
                    "growth_rate": 0.05,
                    "avg_salary": 65000,
                    "job_openings": 75000,
                },
                "General": {
                    "growth_rate": 0.06,
                    "avg_salary": 55000,
                    "job_openings": 100000,
                },
            }

            conditions = market_conditions.get(field, market_conditions["General"])

            # Calculate motivation factor from market conditions
            motivation_factor = self._calculate_job_market_motivation(conditions)

            data_point = ExternalDataPoint(
                source_type=DataSourceType.JOB_MARKET,
                timestamp=datetime.utcnow(),
                value=motivation_factor,
                metadata={
                    "field": field,
                    "growth_rate": conditions["growth_rate"],
                    "avg_salary": conditions["avg_salary"],
                    "job_openings": conditions["job_openings"],
                },
                confidence=0.75,
                freshness_score=0.6,  # Market data changes slowly
            )

            return [data_point]

        except Exception as e:
            logger.error(f"Error getting job market data: {str(e)}")
            return []

    def _calculate_job_market_motivation(self, conditions: Dict[str, float]) -> float:
        """Calculate motivation factor from job market conditions."""
        # Higher growth rate = more motivation
        growth_motivation = min(1.0, conditions["growth_rate"] * 5)

        # Higher salary = more motivation (normalized)
        salary_motivation = min(1.0, conditions["avg_salary"] / 100000)

        # More job openings = more motivation (normalized)
        openings_motivation = min(1.0, conditions["job_openings"] / 100000)

        # Combined motivation factor
        motivation = (
            growth_motivation * 0.4
            + salary_motivation * 0.35
            + openings_motivation * 0.25
        )

        return motivation

    async def _get_industry_trends_data(
        self, course_id: int
    ) -> List[ExternalDataPoint]:
        """Get industry trend data for course relevance."""
        try:
            course = Course.query.get(course_id)
            if not course:
                return []

            # Simulated industry trends
            # In production, could use Google Trends, industry reports, etc.

            trends = {
                "AI/ML": 0.9,
                "Data Science": 0.85,
                "Cybersecurity": 0.8,
                "Cloud Computing": 0.75,
                "General": 0.5,
            }

            # Map course to industry trend
            course_name = course.name.lower()
            trend_value = 0.5  # Default

            for trend, value in trends.items():
                if any(keyword in course_name for keyword in trend.lower().split("/")):
                    trend_value = value
                    break

            data_point = ExternalDataPoint(
                source_type=DataSourceType.INDUSTRY_TRENDS,
                timestamp=datetime.utcnow(),
                value=trend_value,
                metadata={
                    "course_name": course.name,
                    "trend_category": "Technology",  # Could be dynamic
                    "relevance_score": trend_value,
                },
                confidence=0.7,
                freshness_score=0.8,
            )

            return [data_point]

        except Exception as e:
            logger.error(f"Error getting industry trends data: {str(e)}")
            return []

    def get_feature_vector_from_external_data(
        self,
        external_data: Dict[str, List[ExternalDataPoint]],
        feature_window_days: int = 7,
    ) -> np.ndarray:
        """
        Convert external data into a feature vector for ML models.

        Args:
            external_data: Dictionary of external data points
            feature_window_days: Number of days to aggregate features over

        Returns:
            Numpy array of features for ML model input
        """
        try:
            features = []
            current_time = datetime.utcnow()

            # Process each data source type
            for source_type in DataSourceType:
                source_key = source_type.value
                data_points = external_data.get(source_key, [])

                if not data_points:
                    # Add default features if no data available
                    features.extend(
                        [0.5, 0.0, 0.0, 0.5]
                    )  # mean, std, trend, confidence
                    continue

                # Filter to recent data points
                recent_points = [
                    point
                    for point in data_points
                    if (current_time - point.timestamp).days <= feature_window_days
                ]

                if not recent_points:
                    features.extend([0.5, 0.0, 0.0, 0.5])
                    continue

                # Extract numerical features
                values = [point.value for point in recent_points]
                confidences = [point.confidence for point in recent_points]

                # Statistical features
                mean_value = np.mean(values)
                std_value = np.std(values) if len(values) > 1 else 0.0

                # Trend feature (linear regression slope)
                if len(values) > 2:
                    x = np.arange(len(values))
                    trend = np.polyfit(x, values, 1)[0]
                else:
                    trend = 0.0

                # Weighted confidence
                avg_confidence = np.mean(confidences)

                features.extend([mean_value, std_value, trend, avg_confidence])

            return np.array(features)

        except Exception as e:
            logger.error(f"Error creating feature vector: {str(e)}")
            # Return default feature vector if error
            return np.zeros(len(DataSourceType) * 4)

    async def refresh_external_data_cache(self):
        """Refresh cached external data for all active users."""
        try:
            logger.info("Refreshing external data cache")

            # Get active users (users with recent activity)
            active_users = User.query.filter(
                User.last_login > datetime.utcnow() - timedelta(days=30)
            ).all()

            # Refresh data for each user
            for user in active_users:
                try:
                    external_data = await self.get_comprehensive_external_data(user.id)
                    cache_key = f"external_data_{user.id}"
                    self.cache[cache_key] = {
                        "data": external_data,
                        "timestamp": datetime.utcnow(),
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to refresh data for user {user.id}: {str(e)}"
                    )

            logger.info(f"Refreshed external data cache for {len(active_users)} users")

        except Exception as e:
            logger.error(f"Error refreshing external data cache: {str(e)}")

    def get_data_quality_metrics(
        self, external_data: Dict[str, List[ExternalDataPoint]]
    ) -> Dict[str, float]:
        """Calculate data quality metrics for external data."""
        try:
            quality_metrics = {}

            for source_type, data_points in external_data.items():
                if not data_points:
                    quality_metrics[source_type] = {
                        "completeness": 0.0,
                        "freshness": 0.0,
                        "confidence": 0.0,
                        "overall_quality": 0.0,
                    }
                    continue

                # Completeness (data availability)
                completeness = len(data_points) / 30.0  # Expect ~30 data points
                completeness = min(1.0, completeness)

                # Freshness (how recent is the data)
                freshness_scores = [point.freshness_score for point in data_points]
                avg_freshness = np.mean(freshness_scores)

                # Confidence (data reliability)
                confidence_scores = [point.confidence for point in data_points]
                avg_confidence = np.mean(confidence_scores)

                # Overall quality score
                overall_quality = (
                    completeness * 0.4 + avg_freshness * 0.3 + avg_confidence * 0.3
                )

                quality_metrics[source_type] = {
                    "completeness": completeness,
                    "freshness": avg_freshness,
                    "confidence": avg_confidence,
                    "overall_quality": overall_quality,
                }

            return quality_metrics

        except Exception as e:
            logger.error(f"Error calculating data quality metrics: {str(e)}")
            return {}


# Global service instance
external_data_service = ExternalDataIntegrationService()
