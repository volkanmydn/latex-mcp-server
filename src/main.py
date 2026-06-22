import sys
import logging
import subprocess
import tempfile
import re
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from policy import LatexPolicy
from security.validator import validate_latex, LatexSecurityError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


POLICY = LatexPolicy()


TECTONIC_PATH = Path(__file__).parent.parent / "tectonic.exe"


mcp = FastMCP("LaTeX-Compiler-Server")


def turkce_hata_mesaji(log: str) -> str:
    """
    Tectonic hata çıktısını kullanıcı dostu Türkçeye çevirir.
    """

    satir_no = None

    match = re.search(r"document\.tex:(\d+):", log)

    if match:
        satir_no = match.group(1)

    konum = f" (satır {satir_no})" if satir_no else ""


    if "Undefined control sequence" in log:
        return (
            f"❌ Tanımsız komut hatası{konum}\n\n"
            "LaTeX bilinmeyen bir komut gördü.\n"
            "Komut yazımı veya paket eksikliğini kontrol edin."
        )


    if "Missing $ inserted" in log:
        return (
            f"❌ Matematik modu hatası{konum}\n\n"
            "Matematik ifadeleri $ $ arasında olmalı."
        )


    if "not found" in log:
        return (
            f"❌ Eksik dosya veya paket{konum}\n\n"
            "Gerekli dosya bulunamadı."
        )


    if "File ended while scanning" in log:
        return (
            f"❌ Eksik kapatma hatası{konum}\n\n"
            "{ veya } dengesi bozuk."
        )


    if "Too many }" in log:
        return (
            f"❌ Fazladan kapatma parantezi{konum}"
        )


    if "Missing \\begin{document}" in log:
        return (
            "❌ Belge yapısı eksik\n\n"
            "\\documentclass veya \\begin{document} eksik."
        )


    if "Emergency stop" in log:
        return (
            "❌ Kritik LaTeX hatası\n\n"
            "Derleme durduruldu."
        )


    temiz = "\n".join(
        x for x in log.splitlines()
        if x.strip().startswith("!")
        or x.strip().startswith("error:")
    )


    if not temiz:
        temiz = log[-500:]


    return f"❌ Derleme hatası\n\n{temiz}"



@mcp.tool()
def compile_latex(source: str) -> str:
    """
    LaTeX kodunu derler ve PDF üretir.
    """

    # Güvenlik kontrolü

    try:
        validate_latex(source)

    except LatexSecurityError as e:
        return f"❌ Güvenlik hatası: {e}"


    # Kaynak boyutu kontrolü

    if len(source.encode("utf-8")) > POLICY.max_source_size_bytes:
        return "❌ HATA: Kaynak dosya çok büyük."


    with tempfile.TemporaryDirectory() as tmp:

        tmpdir = Path(tmp)

        tex_file = tmpdir / "document.tex"

        tex_file.write_text(
            source,
            encoding="utf-8"
        )


        try:

            result = subprocess.run(
                [
                    str(TECTONIC_PATH),
                    "--outdir",
                    str(tmpdir),
                    str(tex_file)
                ],
                capture_output=True,
                text=True,
                timeout=POLICY.max_timeout_seconds
            )


        except subprocess.TimeoutExpired:

            return (
                "❌ HATA: Derleme zaman aşımına uğradı."
            )


        pdf_path = tmpdir / "document.pdf"


        if pdf_path.exists():

            pdf_bytes = pdf_path.read_bytes()

            pdf_b64 = base64.b64encode(
                pdf_bytes
            ).decode("ascii")


            return (
                "✅ PDF üretildi!\n\n"
                "Base64 PDF:\n"
                f"{pdf_b64}"
            )


        else:

            return turkce_hata_mesaji(
                result.stdout + result.stderr
            )




@mcp.tool()
def get_policy_info() -> str:
    """
    Sistem kurallarını gösterir.
    """

    return f"""
Kurallar:

Max kaynak:
{POLICY.max_source_size_mb} MB

Shell escape:
{'YASAK' if not POLICY.allow_shell_escape else 'AÇIK'}

Network:
{'KAPALI' if not POLICY.allow_network else 'AÇIK'}
"""



if __name__ == "__main__":

    logger.info(
        "Sunucu başlıyor..."
    )

    mcp.run()