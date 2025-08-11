#!/usr/bin/env python3
"""
Shadow Methods Package

This package contains different shadow calculation algorithms for terrain rendering.
Each method is encapsulated for easy comparison and switching.
"""

from .shadow_method_1 import ShadowMethod1
from .shadow_method_2 import ShadowMethod2
from .shadow_method_3 import ShadowMethod3

__all__ = ['ShadowMethod1', 'ShadowMethod2', 'ShadowMethod3']