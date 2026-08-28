# ==================================================================================
# INTERPRETER PARSERS SUBPACKAGE INTERFACE
# ------------------------------------------------------------------------------
# FUNCTIONALITY:
# 1. Package Consolidation: Groups the Metadata Analyzer and Action Parsers 
#    under a single 'parsers' subpackage within the interpreter module.
# 2. Re-Export Layer: Exposes Metadata, MetadataError, MetadataPackage, and 
#    ActionParsers directly from the package root so external modules such as 
#    builder.py can import them without needing to know the internal file layout.
# ==================================================================================

from .metadata import Metadata, MetadataError, MetadataPackage
from .parsers import ActionParsers

__all__ = ["Metadata", "MetadataError", "MetadataPackage", "ActionParsers"]
