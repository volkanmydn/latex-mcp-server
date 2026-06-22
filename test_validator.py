import sys
from pathlib import Path

# .resolve() ekleyerek klasörün tam bilgisayar konumunu (absolute path) buluyoruz
src_path = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_path))

from security.validator import validate_latex, LatexSecurityError

# 1. TEST: Temiz ve kurallara uygun normal bir LaTeX kodu
safe_latex = r"""
\documentclass{article}
\begin{document}
Merhaba Dunya! Bu guvenli bir LaTeX belgesidir.
\end{document}
"""

# 2. TEST: Sisteme sızmaya çalışan (\write18 içeren) zararlı bir LaTeX kodu
unsafe_latex = r"""
\documentclass{article}
\begin{document}
Zararli komut calistirma denemesi:
\write18{echo "Sistem Hacklendi"}
\end{document}
"""

print("\n--- 🛡️ LATEX MCP SERVER GÜVENLİK TESTLERİ 🛡️ ---\n")

# --- Normal Kod Testi ---
print("1. Test Başlatılıyor (Güvenli Kod)...")
try:
    validate_latex(safe_latex)
    print("✅ BAŞARILI: Güvenli LaTeX koduna geçiş izni verildi.")
except LatexSecurityError as e:
    print(f"❌ BAŞARISIZ: Güvenli koda temiz olduğu halde hata verdi: {e}")

print("-" * 40)

# --- Sabotaj Testi (\write18) ---
print("2. Test Başlatılıyor (Zararlı Kod - \\write18)...")
try:
    validate_latex(unsafe_latex)
    print("❌ BAŞARISIZ: Büyük güvenlik açığı! Zararlı kod engellenemedi!")
except LatexSecurityError as e:
    print(f"✅ BAŞARILI: Güvenlik duvarı çalıştı! Zararlı kod engellendi.")
    print(f" Yakalanan Hata Mesajı: {e}\n")
