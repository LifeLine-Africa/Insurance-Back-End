"""
Comprehensive test suite for LifeLine Africa Insurance API
Tests all endpoints, validation, error handling, and edge cases
"""

from flask.config import Config
import pytest
import json
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import uuid


class TestConfig(Config):
    """Test configuration with in-memory database"""
    TESTING = True
    import os
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/testdb')
    SECRET_KEY = 'test-secret-key'
    SMTP_USERNAME = 'SMTP_USERNAME'
    SMTP_PASSWORD = 'SMTP_PASSWORD'
