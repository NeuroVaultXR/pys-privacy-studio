"""A monitored budget, not a reservation or an exact operating-system RAM cap."""
def profile(budget_gib):
    budget=max(1,float(budget_gib))
    return {'budget':budget,'dpi':150 if budget<8 else 180,
            'context':1024 if budget<8 else 2048,'chunk':2500 if budget<8 else 5000,
            'unload_between_stages':budget<24}
