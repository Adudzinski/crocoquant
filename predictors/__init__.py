# predictors/__init__.py
"""
Auto-discover every module in this folder that exposes
a callable named `predict(price_df, **params)`.
"""

import pkgutil, importlib, inspect, pathlib

PREDICTORS = {}

# Iterate over sibling .py files (skip __init__.py itself)
package_path = pathlib.Path(__file__).parent
for _, mod_name, _ in pkgutil.iter_modules([package_path.as_posix()]):
    module = importlib.import_module(f"{__name__}.{mod_name}")
    if hasattr(module, "predict") and inspect.isfunction(module.predict):
        PREDICTORS[mod_name] = module.predict

