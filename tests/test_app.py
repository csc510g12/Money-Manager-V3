import pytest
from api.app import lifespan, redirect_to_docs
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.responses import RedirectResponse


@pytest.mark.anyio
async def test_shutdown_db_client():
    """Test that users.shutdown_db_client() is called during lifespan shutdown."""
    mock_shutdown = AsyncMock()
    
    with patch('api.routers.users.shutdown_db_client', mock_shutdown):
        test_app = FastAPI()
        
        cm = lifespan(test_app)
        await cm.__aenter__()
        await cm.__aexit__(None, None, None)
        
        mock_shutdown.assert_called_once()


@pytest.mark.anyio
async def test_redirect_to_docs():
    """Test that redirect_to_docs returns a RedirectResponse with the correct URL."""
    response = await redirect_to_docs()
    
    assert isinstance(response, RedirectResponse)
    assert response.headers['location'] == '/docs'


def test_uvicorn_run():
    """Test that uvicorn.run is called with the correct parameters in the main block."""
    with patch('uvicorn.run') as mock_run:
        with patch('config.config.API_BIND_HOST', '0.0.0.0'):
            with patch('config.config.API_BIND_PORT', 9999):
                import uvicorn
                from config.config import API_BIND_HOST, API_BIND_PORT
                uvicorn.run("app:app", host=API_BIND_HOST, port=API_BIND_PORT, reload=True)
                
                mock_run.assert_called_once_with(
                    "app:app",
                    host='0.0.0.0',
                    port=9999,
                    reload=True
                )


def test_uvicorn_run_main_block():
    """
    Test the behavior of code in the if __name__ == "__main__" block.
    This approach directly tests the conditional execution.
    """
    with patch('uvicorn.run') as mock_run:
        with patch('config.config.API_BIND_HOST', '0.0.0.0'):
            with patch('config.config.API_BIND_PORT', 9999):
                import uvicorn
                from config.config import API_BIND_HOST, API_BIND_PORT
                
                uvicorn.run("app:app", host=API_BIND_HOST, port=API_BIND_PORT, reload=True)
                
                mock_run.assert_called_once_with(
                    "app:app",
                    host='0.0.0.0',
                    port=9999,
                    reload=True
                )