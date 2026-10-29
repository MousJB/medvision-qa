"""Entry point of the public demo deployed on Vercel (Python runtime, one function).

Vercel finds the FastAPI instance ``app`` in this file. It is the same web interface as
``python -m medvision_qa.web``, in public demo mode: nothing is stored, no shared history
(see ``medvision_qa.web``). The bundled examples are read from this folder.
"""

from pathlib import Path

from medvision_qa.web import create_app

app = create_app(public_demo=True, project_root=Path(__file__).resolve().parent)
