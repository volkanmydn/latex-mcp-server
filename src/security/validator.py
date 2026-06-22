import re


class LatexSecurityError(Exception):
    pass


BLOCKED_PATTERNS = [
    r"\\write18",
    r"\\input\s*\{/",
    r"\\include\s*\{/",
    r"\\openout",
    r"\\read",
    r"\\catcode",
]


def validate_latex(source: str) -> None:
    """
    LaTeX kaynağını güvenlik açısından kontrol eder.

    Tehlikeli komut bulunursa hata fırlatır.
    """

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, source):
            raise LatexSecurityError(
                "Güvenlik nedeniyle bu LaTeX komutuna izin verilmiyor."
            )