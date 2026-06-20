from dataclasses import dataclass

@dataclass(frozen=True)
class LatexPolicy:
    
    max_source_size_mb: int = 2
    max_pdf_size_mb: int = 50
    max_log_size_mb: int = 10
    max_timeout_seconds: int = 120
    
    allow_network: bool = False
    allow_shell_escape: bool = False
    auto_install_packages: bool = False

    @property
    def max_source_size_bytes(self) -> int:
        return self.max_source_size_mb * 1024 * 1024