"""
Tracker Model - MIGRATED TO PREPARACION

This model has been migrated to use the Preparacion model as the single source of truth.
All tracker functionality now queries Preparacion.objects.filter(estado_modulo=2).

Historical Note:
- Previous Tracker model fields are now in Preparacion
- The tracker app remains active for API routing and WebSocket support
- Migration completed: December 31, 2025

See: preparacion/models.py for the unified model
"""

# No models defined - tracker functionality uses Preparacion model
