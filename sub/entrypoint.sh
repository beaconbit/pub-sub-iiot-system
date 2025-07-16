#!/bin/bash
# alembic revision --autogenerate -m "create snapshot table"
alembic upgrade head
python main.py
