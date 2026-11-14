import sys
import os

# Adiciona a pasta projeto-Movida ao caminho do Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'projeto-Movida'))

from main import app
