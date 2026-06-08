"""Tests for wsgi module - imports the real module."""
import pytest
import sys
from pathlib import Path


class TestWsgiModule:
    """Test wsgi module can be imported and is correctly configured."""

    def test_wsgi_module_importable(self):
        """Test that wsgi module can be imported."""
        import wsgi
        assert wsgi is not None

    def test_wsgi_has_application(self):
        """Test wsgi exports an application object."""
        import wsgi
        # wsgi should expose the Flask app as 'application' or 'app'
        has_app = hasattr(wsgi, 'application') or hasattr(wsgi, 'app')
        assert has_app

    def test_wsgi_application_is_callable(self):
        """Test that the wsgi application is callable."""
        import wsgi
        if hasattr(wsgi, 'application'):
            assert callable(wsgi.application)
        elif hasattr(wsgi, 'app'):
            assert callable(wsgi.app)
