"""Typed Adapter contract."""

from typing import Protocol

from .models import AdapterInvocation, AdapterMetadata, AdapterResult


class Adapter(Protocol):
    @property
    def metadata(self) -> AdapterMetadata: ...

    def invoke(self, invocation: AdapterInvocation) -> AdapterResult: ...
