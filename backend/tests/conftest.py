"""
Fixtures partagees. Les tests essentiels ciblent les modules purs (moteur de
score, NLP, indicateurs techniques, backtesting) qui ne dependent pas d'une
base de donnees reelle - conformement au principe d'explicabilite : ce sont
les modules les plus sensibles du produit et les plus faciles a isoler.
"""
import pytest


@pytest.fixture(autouse=True)
def _pytest_asyncio_mode():
    yield
