"""
Tracker Admin - MIGRATED TO PREPARACION

The Tracker model has been migrated to use Preparacion as the single source of truth.
Admin functionality for tracker module is now managed through the Preparacion admin
with estado_modulo filtering.

See: preparacion/admin.py for admin configuration
"""

# No admin registration - tracker functionality uses Preparacion model
