"""Lens-specific prompt overlays and crisis detection."""

CRISIS_KEYWORDS = [
    "intihar",
    "kendimi öldür",
    "ölmek istiyorum",
    "yaşamak istemiyorum",
    "kendime zarar",
]

CRISIS_RESPONSE = (
    "Şu an çok ağır bir yerde olabilirsin. Bu sohbet profesyonel destek yerine geçmez.\n"
    "Lütfen bir uzmana veya acil hattına ulaş: ALO 182 (SABIM) veya 112."
)

FREE_MODE_ADDENDUM = """
Serbest mod aktif:
- Daha uzun, keşif odaklı yanıtlar ver.
- Yapılandırılmış akış veya rapor hatırlatması yapma.
- Kullanıcının ritmine uy, soruları derinleştir.
"""
