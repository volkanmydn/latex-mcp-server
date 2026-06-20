import sys
import logging
import subprocess
import tempfile
import shutil
import uuid
import re
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from policy import LatexPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLICY = LatexPolicy()

TECTONIC_PATH = Path(__file__).parent.parent / "tectonic.exe"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

mcp = FastMCP("LaTeX-Compiler-Server")


def turkce_hata_mesaji(log: str) -> str:
    """Tectonic'in ham hata çıktısını anlaşılır Türkçeye çevirir."""

    satir_no = None
    match = re.search(r"document\.tex:(\d+):", log)
    if match:
        satir_no = match.group(1)
    konum = f" (satır {satir_no})" if satir_no else ""

    if "Undefined control sequence" in log:
        return (
            f"❌ Tanımsız komut hatası{konum}\n\n"
            f"Kodunuzda LaTeX'in tanımadığı bir komut var. Olası sebepler:\n"
            f"- Komutu yanlış yazmış olabilirsiniz (örn: \\textb yerine \\textbf)\n"
            f"- Komutun ait olduğu paketi \\usepackage ile eklemeyi unutmuş olabilirsiniz\n"
        )

    if "Missing $ inserted" in log or "Missing \\$" in log:
        return (
            f"❌ Matematik modu hatası{konum}\n\n"
            f"Matematiksel bir ifade $ işaretleri arasına alınmamış.\n"
            f"Örnek doğru kullanım: $x^2 + y^2 = z^2$\n"
        )

    if "File `" in log and "not found" in log:
        pkg_match = re.search(r"File `(.+?)'", log)
        pkg_name = pkg_match.group(1) if pkg_match else "bilinmeyen dosya"
        return (
            f"❌ Eksik paket veya dosya: {pkg_name}\n\n"
            f"Bu paket sistemde bulunamadı. Farklı bir paket deneyin "
            f"veya paket adını kontrol edin.\n"
        )
# Dosya bitti ama bir komut/grup hala açık (eksik kapanış parantezi)
    if "File ended while scanning" in log:
        komut_match = re.search(r"scanning use of (\\?\w+)", log)
        komut = komut_match.group(1) if komut_match else "bir komut"
        return (
            f"❌ Eksik kapatma parantezi{konum}\n\n"
            f"{komut} komutunuz açılmış ama kapatılmamış. "
            f"Her {{ için bir }} olduğundan emin olun. Dosya bu eksik "
            f"yüzünden tamamen bitmiş ve LaTeX kapatmayı bekleyemeden durmuş.\n"
        )
    if "Too many }'s" in log:
        return (
            f"❌ Fazladan kapatma parantezi{konum}\n\n"
            f"Kodunuzda fazladan bir }} işareti var. Parantezlerinizi "
            f"eşleştirip kontrol edin.\n"
        )

    if "Missing } inserted" in log or "Missing {" in log:
        return (
            f"❌ Eksik küme parantezi{konum}\n\n"
            f"Bir {{ veya }} işareti eksik kalmış. Her açılan {{ için "
            f"bir kapanan }} olduğundan emin olun.\n"
        )

    if "\\begin{" in log and "ended by" in log:
        return (
            f"❌ Ortam eşleşme hatası{konum}\n\n"
            f"Bir \\begin{{...}} ile açılan ortam, farklı bir isimle "
            f"\\end{{...}} ile kapatılmaya çalışılmış. Örneğin "
            f"\\begin{{itemize}} açıp \\end{{enumerate}} ile kapatmak gibi.\n"
            f"Aynı isimle açıp kapattığınızdan emin olun.\n"
        )

    if "Missing \\begin{document}" in log:
        return (
            f"❌ Belge yapısı eksik\n\n"
            f"Kodun başında \\documentclass{{...}} ve \\begin{{document}} "
            f"komutları olmalı. Bunlardan biri eksik veya yanlış sırada.\n"
        )

    if "too deeply nested" in log:
        return (
            f"❌ Çok fazla iç içe geçmiş yapı{konum}\n\n"
            f"Parantezleriniz veya ortamlarınız çok derin iç içe geçmiş. "
            f"Yapıyı basitleştirmeyi deneyin.\n"
        )

    if "includegraphics" in log and ("not found" in log or "No such file" in log):
        return (
            f"❌ Resim dosyası bulunamadı{konum}\n\n"
            f"\\includegraphics ile eklemeye çalıştığınız resim dosyası "
            f"bulunamadı. Dosya adını ve yolunu kontrol edin.\n"
        )

    if "Emergency stop" in log:
        return (
            f"❌ Kritik hata\n\n"
            f"Derleme aniden durdu. Genellikle eksik \\end{{document}} "
            f"veya kapanmamış bir parantez/küme parantezi yüzünden olur.\n"
        )

    kisa_log = "\n".join(
        line for line in log.splitlines()
        if line.strip().startswith("error:") or line.strip().startswith("!")
    )
    if not kisa_log:
        kisa_log = log[-500:]

    return f"❌ Derleme hatası\n\nDetay:\n{kisa_log}"


@mcp.tool()
def compile_latex(source: str) -> str:
    """LaTeX kodunu derler ve PDF üretir. Üretilen PDF'in dosya yolunu döner."""

    if len(source.encode("utf-8")) > POLICY.max_source_size_bytes:
        return "❌ HATA: Kaynak dosya çok büyük."

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tex_file = tmpdir / "document.tex"
        tex_file.write_text(source, encoding="utf-8")

        try:
            result = subprocess.run(
                [str(TECTONIC_PATH), "--outdir", str(tmpdir), str(tex_file)],
                capture_output=True,
                text=True,
                timeout=POLICY.max_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return "❌ HATA: Derleme zaman aşımına uğradı (kod çok karmaşık veya sonsuz döngü olabilir)."

        pdf_path = tmpdir / "document.pdf"

        if pdf_path.exists():
            pdf_bytes = pdf_path.read_bytes()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
            return f"✅ PDF üretildi!\n\nBase64 PDF verisi:\n{pdf_b64}"
        else:
            ham_log = result.stdout + result.stderr
            return turkce_hata_mesaji(ham_log)


@mcp.tool()
def get_policy_info() -> str:
    """Sistem kurallarını gösterir."""
    return f"""
Kurallar:
- Max dosya: {POLICY.max_source_size_mb} MB
- Shell escape: {'YASAK' if not POLICY.allow_shell_escape else 'İZİN VAR'}
- Ağ: {'KAPALI' if not POLICY.allow_network else 'AÇIK'}
"""


if __name__ == "__main__":
    logger.info("Sunucu başlıyor...")
    mcp.run()